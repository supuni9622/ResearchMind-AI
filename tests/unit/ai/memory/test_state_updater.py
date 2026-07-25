from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from app.ai.memory.enums import MemoryType
from app.ai.memory.models import MemoryRecord
from app.ai.memory.services.memory_service import MemoryService
from app.ai.memory.session.state_updater import (
    SessionStateDistillation,
    SessionStateUpdaterService,
    distill_and_upsert_session_state,
)
from app.ai.runtime.generation.enums import GenerationProvider


def _record(*, kind: str, content: str = "content") -> MemoryRecord:
    now = datetime.now(UTC)
    return MemoryRecord(
        id=uuid4(),
        owner_id=uuid4(),
        type=MemoryType.SESSION,
        content=content,
        metadata={"kind": kind},
        importance_score=1.0,
        created_at=now,
        updated_at=now,
    )


# ==========================================================
# SessionStateUpdaterService.distill()
# ==========================================================


async def test_distill_uses_the_configured_provider() -> None:
    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(
        parsed_output=SessionStateDistillation(has_topic=True, content="Topic: earthquakes"),
    )
    service = SessionStateUpdaterService(runtime, provider=GenerationProvider.GROQ)

    result = await service.distill(user_message="research earthquakes")

    assert result is not None
    assert result.has_topic is True
    assert result.content == "Topic: earthquakes"
    runtime.execute.assert_awaited_once()
    assert runtime.execute.await_args.kwargs["provider"] == GenerationProvider.GROQ


async def test_distill_falls_back_to_the_fallback_provider_on_primary_failure() -> None:
    runtime = AsyncMock()
    runtime.execute.side_effect = [
        RuntimeError("primary down"),
        SimpleNamespace(parsed_output=SessionStateDistillation(has_topic=True, content="ok")),
    ]
    service = SessionStateUpdaterService(
        runtime, provider=GenerationProvider.GROQ, fallback_provider=GenerationProvider.OPENAI
    )

    result = await service.distill(user_message="research earthquakes")

    assert result is not None
    assert result.content == "ok"
    assert runtime.execute.await_count == 2


async def test_distill_returns_none_when_both_providers_fail() -> None:
    runtime = AsyncMock()
    runtime.execute.side_effect = RuntimeError("down")
    service = SessionStateUpdaterService(
        runtime, provider=GenerationProvider.GROQ, fallback_provider=GenerationProvider.OPENAI
    )

    result = await service.distill(user_message="research earthquakes")

    assert result is None


async def test_distill_returns_none_for_non_schema_output() -> None:
    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(parsed_output="not a schema object")
    service = SessionStateUpdaterService(runtime, provider=GenerationProvider.GROQ)

    result = await service.distill(user_message="research earthquakes")

    assert result is None


async def test_distill_includes_previous_state_in_the_prompt() -> None:
    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(
        parsed_output=SessionStateDistillation(has_topic=True, content="updated"),
    )
    service = SessionStateUpdaterService(runtime, provider=GenerationProvider.GROQ)

    await service.distill(
        user_message="so how does magma relate to it?",
        assistant_message="Magma feeds volcanic activity...",
        previous_state="Topic: earthquakes and their causes",
    )

    request = runtime.execute.await_args.args[0]
    assert "Topic: earthquakes and their causes" in request.prompt_context.context
    assert "so how does magma relate to it?" in request.prompt_context.context


# ==========================================================
# MemoryService.get_latest_session_state()
# ==========================================================


async def test_get_latest_session_state_returns_none_when_nothing_matches() -> None:
    session = AsyncMock()
    session.get_context = AsyncMock(return_value=[_record(kind="raw_turn")])
    service = MemoryService(
        session_memory=session,
        user_memory=AsyncMock(),
        semantic_memory=AsyncMock(),
        research_memory=AsyncMock(),
    )

    result = await service.get_latest_session_state(
        owner_id=uuid4(), session_id=uuid4(), kind="current_topic"
    )

    assert result is None


async def test_get_latest_session_state_returns_the_most_recent_match() -> None:
    older = _record(kind="current_topic", content="old topic")
    newer = _record(kind="current_topic", content="new topic")
    session = AsyncMock()
    session.get_context = AsyncMock(return_value=[older, newer])
    service = MemoryService(
        session_memory=session,
        user_memory=AsyncMock(),
        semantic_memory=AsyncMock(),
        research_memory=AsyncMock(),
    )

    result = await service.get_latest_session_state(
        owner_id=uuid4(), session_id=uuid4(), kind="current_topic"
    )

    assert result is not None
    assert result.content == "new topic"


# ==========================================================
# distill_and_upsert_session_state()
# ==========================================================


def _updater(*, distillation: SessionStateDistillation | None) -> AsyncMock:
    updater = AsyncMock(spec=SessionStateUpdaterService)
    updater.distill = AsyncMock(return_value=distillation)
    return updater


async def test_upsert_remembers_a_new_record_when_none_exists() -> None:
    memory_service = AsyncMock(spec=MemoryService)
    memory_service.get_latest_session_state = AsyncMock(return_value=None)
    updater = _updater(distillation=SessionStateDistillation(has_topic=True, content="earthquakes"))

    await distill_and_upsert_session_state(
        memory_service=memory_service,
        session_state_updater=updater,
        owner_id=uuid4(),
        session_id=uuid4(),
        user_message="research earthquakes",
        assistant_message="Sure, here's an overview...",
        turn_id="turn-1",
    )

    memory_service.remember.assert_awaited_once()
    memory_service.update_memory.assert_not_awaited()
    assert memory_service.remember.await_args.kwargs["content"] == "earthquakes"
    assert memory_service.remember.await_args.kwargs["metadata"]["kind"] == "current_topic"


async def test_upsert_updates_the_existing_record_in_place() -> None:
    existing = _record(kind="current_topic", content="earthquakes")
    memory_service = AsyncMock(spec=MemoryService)
    memory_service.get_latest_session_state = AsyncMock(return_value=existing)
    updater = _updater(
        distillation=SessionStateDistillation(
            has_topic=True, content="earthquakes and their relation to magma"
        )
    )

    await distill_and_upsert_session_state(
        memory_service=memory_service,
        session_state_updater=updater,
        owner_id=uuid4(),
        session_id=uuid4(),
        user_message="so how magma related to it?",
        assistant_message="Magma feeds volcanic activity...",
        turn_id="turn-2",
    )

    memory_service.update_memory.assert_awaited_once()
    memory_service.remember.assert_not_awaited()
    assert memory_service.update_memory.await_args.kwargs["memory_id"] == existing.id
    assert (
        memory_service.update_memory.await_args.kwargs["content"]
        == "earthquakes and their relation to magma"
    )


async def test_upsert_writes_nothing_when_distillation_has_no_topic() -> None:
    memory_service = AsyncMock(spec=MemoryService)
    memory_service.get_latest_session_state = AsyncMock(return_value=None)
    updater = _updater(distillation=SessionStateDistillation(has_topic=False, content=""))

    await distill_and_upsert_session_state(
        memory_service=memory_service,
        session_state_updater=updater,
        owner_id=uuid4(),
        session_id=uuid4(),
        user_message="thanks!",
        assistant_message="You're welcome.",
        turn_id="turn-3",
    )

    memory_service.remember.assert_not_awaited()
    memory_service.update_memory.assert_not_awaited()


async def test_upsert_writes_nothing_when_distillation_fails() -> None:
    memory_service = AsyncMock(spec=MemoryService)
    memory_service.get_latest_session_state = AsyncMock(return_value=None)
    updater = _updater(distillation=None)

    await distill_and_upsert_session_state(
        memory_service=memory_service,
        session_state_updater=updater,
        owner_id=uuid4(),
        session_id=uuid4(),
        user_message="research earthquakes",
        assistant_message="Sure.",
        turn_id="turn-4",
    )

    memory_service.remember.assert_not_awaited()
    memory_service.update_memory.assert_not_awaited()
