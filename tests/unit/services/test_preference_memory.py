from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.ai.memory.enums import MemoryType
from app.models.enums import FeedbackSurface
from app.services.preference_memory import PreferenceMemoryWriter


def _session_factory(session: MagicMock) -> MagicMock:
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=session)
    context.__aexit__ = AsyncMock(return_value=None)
    factory = MagicMock(return_value=context)
    return factory


@pytest.mark.asyncio
async def test_commits_the_separately_owned_session_after_memory_succeeds() -> None:
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    memory_service = MagicMock()
    memory_service.remember_extracted = AsyncMock(return_value=(None, "created"))
    service_factory = MagicMock(return_value=memory_service)
    writer = PreferenceMemoryWriter(
        session_factory=_session_factory(session),
        memory_service_factory=service_factory,
    )
    owner_id = uuid4()
    generation_id = uuid4()

    await writer.remember_feedback_preference(
        owner_id=owner_id,
        generation_id=generation_id,
        surface=FeedbackSurface.CHAT,
        content="Please keep answers concise",
        importance_score=0.8,
    )

    service_factory.assert_called_once_with(session)
    memory_service.remember_extracted.assert_awaited_once_with(
        owner_id=owner_id,
        type=MemoryType.USER,
        content="Please keep answers concise",
        importance_score=0.8,
        metadata={
            "source": "feedback",
            "generation_id": str(generation_id),
            "surface": FeedbackSurface.CHAT.value,
        },
    )
    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_rolls_back_only_the_owned_session_and_reraises_on_failure() -> None:
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    memory_service = MagicMock()
    memory_service.remember_extracted = AsyncMock(side_effect=RuntimeError("write failed"))
    writer = PreferenceMemoryWriter(
        session_factory=_session_factory(session),
        memory_service_factory=MagicMock(return_value=memory_service),
    )

    with pytest.raises(RuntimeError, match="write failed"):
        await writer.remember_feedback_preference(
            owner_id=uuid4(),
            generation_id=uuid4(),
            surface=FeedbackSurface.LINEAR_RESEARCH,
            content="Prefer tables",
            importance_score=0.6,
        )

    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_rolls_back_when_commit_itself_fails() -> None:
    session = MagicMock()
    session.commit = AsyncMock(side_effect=RuntimeError("commit failed"))
    session.rollback = AsyncMock()
    memory_service = MagicMock()
    memory_service.remember_extracted = AsyncMock(return_value=(None, "created"))
    writer = PreferenceMemoryWriter(
        session_factory=_session_factory(session),
        memory_service_factory=MagicMock(return_value=memory_service),
    )

    with pytest.raises(RuntimeError, match="commit failed"):
        await writer.remember_feedback_preference(
            owner_id=uuid4(),
            generation_id=uuid4(),
            surface=FeedbackSurface.DEEP_RESEARCH,
            content="Prefer detailed reports",
            importance_score=0.7,
        )

    session.rollback.assert_awaited_once()
