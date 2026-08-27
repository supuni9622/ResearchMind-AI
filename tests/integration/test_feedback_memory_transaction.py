"""Database proof that optional memory failure cannot undo feedback."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from app.ai.runtime.generation.comment_classification.models import (
    CommentClassificationDecision,
)
from app.models.enums import CommentClassification, FeedbackRating, FeedbackSurface
from app.models.eval_score import EvalScore
from app.models.feedback import Feedback
from app.models.user import User
from app.repositories.eval_score import EvalScoreRepository
from app.repositories.feedback import FeedbackRepository
from app.repositories.generation_usage import GenerationUsageRepository
from app.services.feedback import FeedbackService
from app.services.preference_memory import PreferenceMemoryWriter
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


@pytest.mark.asyncio
async def test_memory_commit_failure_does_not_rollback_committed_feedback(test_engine) -> None:
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        autoflush=False,
        expire_on_commit=False,
    )
    owner_id = uuid4()
    generation_id = uuid4()
    duplicate_email = f"m0-{owner_id}@example.com"

    async with session_factory() as setup_session:
        setup_session.add(
            User(
                id=owner_id,
                auth_provider="test",
                provider_user_id=str(owner_id),
                email=duplicate_email,
            )
        )
        await setup_session.commit()

    class _FailingMemoryService:
        def __init__(self, session: AsyncSession) -> None:
            self._session = session

        async def remember_extracted(self, **_: object) -> tuple[None, str]:
            # The duplicate email violates users.email's real unique index at
            # writer commit time, leaving only the writer's session failed.
            self._session.add(
                User(
                    id=uuid4(),
                    auth_provider="test",
                    provider_user_id=str(uuid4()),
                    email=duplicate_email,
                )
            )
            return None, "created"

    writer = PreferenceMemoryWriter(
        session_factory=session_factory,
        memory_service_factory=_FailingMemoryService,  # type: ignore[arg-type]
    )
    classification = MagicMock()
    classification.classify = AsyncMock(
        return_value=CommentClassificationDecision(
            classification=CommentClassification.PREFERENCE,
            reason="style preference",
        )
    )

    async with session_factory() as request_session:
        service = FeedbackService(
            session=request_session,
            repository=FeedbackRepository(request_session),
            generation_usage_repository=GenerationUsageRepository(request_session),
            eval_score_repository=EvalScoreRepository(request_session),
            comment_classification_service=classification,
            preference_memory_writer=writer,
        )
        with patch("app.services.feedback.sync_user_feedback"):
            result = await service.submit(
                owner_id=owner_id,
                generation_id=generation_id,
                surface=FeedbackSurface.CHAT,
                rating=FeedbackRating.DOWN,
                comment="Please be less formal",
            )

    assert result.owner_id == owner_id

    async with session_factory() as verification_session:
        persisted_feedback = (
            await verification_session.execute(
                select(Feedback).where(
                    Feedback.owner_id == owner_id,
                    Feedback.generation_id == generation_id,
                )
            )
        ).scalar_one()
        persisted_score = (
            await verification_session.execute(
                select(EvalScore).where(
                    EvalScore.owner_id == owner_id,
                    EvalScore.generation_id == generation_id,
                    EvalScore.metric_name == "user_rating",
                )
            )
        ).scalar_one()

    assert persisted_feedback.comment == "Please be less formal"
    assert persisted_feedback.comment_classification == "preference"
    assert persisted_score.score == 0.0
    assert persisted_score.comment_classification == "preference"

    # This test must use real commits to prove the transaction boundary, so it
    # cannot rely on the suite's usual outer-transaction rollback fixture.
    # Remove its owner explicitly; FK cascades clean feedback/eval rows before
    # later repository tests perform platform-wide candidate queries.
    async with session_factory() as cleanup_session:
        await cleanup_session.execute(delete(User).where(User.id == owner_id))
        await cleanup_session.commit()
