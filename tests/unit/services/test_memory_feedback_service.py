from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.models.enums import EvalScoreSource, FeedbackSurface, MemoryFeedbackSignal
from app.models.memory_feedback import MemoryFeedback
from app.services.memory_feedback import MEMORY_USER_SIGNAL_METRIC, MemoryFeedbackService
from fastapi import HTTPException


async def test_memory_feedback_requires_an_owned_memory_backed_generation() -> None:
    generation_repository = MagicMock()
    generation_repository.get_owned_generation = AsyncMock(return_value=None)
    service = MemoryFeedbackService(
        session=MagicMock(),
        repository=MagicMock(),
        generation_usage_repository=generation_repository,
        eval_score_repository=MagicMock(),
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.submit(
            owner_id=uuid4(),
            generation_id=uuid4(),
            surface=FeedbackSurface.CHAT,
            signal=MemoryFeedbackSignal.HELPED,
        )

    assert exc_info.value.status_code == 404


async def test_memory_feedback_is_persisted_and_mirrored_to_eval_scores() -> None:
    owner_id = uuid4()
    generation_id = uuid4()
    generation = MagicMock(injected_memory_ids=[uuid4()])
    stored = MemoryFeedback(
        id=uuid4(),
        owner_id=owner_id,
        generation_id=generation_id,
        surface=FeedbackSurface.CHAT.value,
        signal=MemoryFeedbackSignal.WRONG.value,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session = MagicMock()
    session.commit = AsyncMock()
    repository = MagicMock()
    repository.upsert = AsyncMock(return_value=stored)
    generation_repository = MagicMock()
    generation_repository.get_owned_generation = AsyncMock(return_value=generation)
    eval_repository = MagicMock()
    eval_repository.upsert = AsyncMock()
    service = MemoryFeedbackService(
        session=session,
        repository=repository,
        generation_usage_repository=generation_repository,
        eval_score_repository=eval_repository,
    )

    result = await service.submit(
        owner_id=owner_id,
        generation_id=generation_id,
        surface=FeedbackSurface.CHAT,
        signal=MemoryFeedbackSignal.WRONG,
    )

    assert result is stored
    eval_repository.upsert.assert_awaited_once_with(
        owner_id=owner_id,
        generation_id=generation_id,
        metric_name=MEMORY_USER_SIGNAL_METRIC,
        score=0.0,
        passed=False,
        reason="user reported memory wrong",
        source=EvalScoreSource.HUMAN_FEEDBACK.value,
    )
    session.commit.assert_awaited_once()
