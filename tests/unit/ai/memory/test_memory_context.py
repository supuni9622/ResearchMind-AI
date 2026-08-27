from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

from app.ai.memory.enums import MemoryScopeType, MemoryType
from app.ai.memory.models import MemoryRecord
from app.ai.memory.services.memory_service import MemoryService


def _record(memory_type: MemoryType) -> MemoryRecord:
    now = datetime.now(UTC)
    return MemoryRecord(
        id=uuid4(),
        owner_id=uuid4(),
        type=memory_type,
        content=f"{memory_type} memory",
        importance_score=0.8,
        created_at=now,
        updated_at=now,
    )


async def test_context_skips_embedding_when_no_durable_memory() -> None:
    session = AsyncMock()
    session.get_context = AsyncMock(return_value=[])
    user = AsyncMock()
    user.list_preferences = AsyncMock(return_value=[])
    semantic = AsyncMock()
    research = AsyncMock()
    availability = AsyncMock()
    availability.has_durable_memory = AsyncMock(return_value=False)
    service = MemoryService(
        session_memory=session,
        user_memory=user,
        semantic_memory=semantic,
        research_memory=research,
        availability_service=availability,
    )
    await service.get_context(owner_id=uuid4(), session_id=uuid4(), semantic_query="question")
    semantic.embed_query.assert_not_awaited()
    semantic.search_with_embedding.assert_not_awaited()
    research.search_with_embedding.assert_not_awaited()


async def test_context_uses_one_embedding_and_preserves_successful_parallel_branch() -> None:
    session = AsyncMock()
    session.get_context = AsyncMock(return_value=[])
    user = AsyncMock()
    user.list_preferences = AsyncMock(return_value=[])
    semantic = AsyncMock()
    semantic.embed_query = AsyncMock(return_value=[0.1, 0.2])
    semantic.search_with_embedding = AsyncMock(return_value=[_record(MemoryType.SEMANTIC)])
    research = AsyncMock()
    research.search_with_embedding = AsyncMock(side_effect=RuntimeError("qdrant failure"))
    availability = AsyncMock()
    availability.has_durable_memory = AsyncMock(return_value=True)
    service = MemoryService(
        session_memory=session,
        user_memory=user,
        semantic_memory=semantic,
        research_memory=research,
        availability_service=availability,
    )
    context = await service.get_context(
        owner_id=uuid4(), session_id=uuid4(), semantic_query="question"
    )
    assert len(context.semantic_memories) == 1
    assert context.research_memories == []
    semantic.embed_query.assert_awaited_once()
    semantic.search_with_embedding.assert_awaited_once()


async def test_context_includes_user_preferences() -> None:
    session = AsyncMock()
    session.get_context = AsyncMock(return_value=[])
    user = AsyncMock()
    preference = _record(MemoryType.USER)
    user.list_preferences = AsyncMock(return_value=[preference])
    semantic = AsyncMock()
    research = AsyncMock()
    service = MemoryService(
        session_memory=session,
        user_memory=user,
        semantic_memory=semantic,
        research_memory=research,
    )
    context = await service.get_context(owner_id=uuid4(), session_id=uuid4(), top_k=7)
    assert context.user_memories == [preference]
    user.list_preferences.assert_awaited_once()
    _, kwargs = user.list_preferences.await_args
    assert kwargs["limit"] == 7


async def test_project_context_inherits_personal_user_only_and_scopes_other_memory() -> None:
    owner_id = uuid4()
    project_id = uuid4()
    personal_preference = _record(MemoryType.USER)
    project_preference = _record(MemoryType.USER).model_copy(
        update={"scope_type": MemoryScopeType.PROJECT, "project_id": project_id}
    )
    session = AsyncMock()
    session.get_context = AsyncMock(return_value=[])
    user = AsyncMock()
    user.list_preferences = AsyncMock(side_effect=[[personal_preference], [project_preference]])
    service = MemoryService(
        session_memory=session,
        user_memory=user,
        semantic_memory=AsyncMock(),
        research_memory=AsyncMock(),
    )

    context = await service.get_context(
        owner_id=owner_id,
        session_id=uuid4(),
        scope_type=MemoryScopeType.PROJECT,
        project_id=project_id,
    )

    assert context.user_memories == [personal_preference, project_preference]
    session.get_context.assert_awaited_once()
    assert session.get_context.await_args.kwargs["project_id"] == project_id
    assert user.list_preferences.await_args_list[0].kwargs["project_id"] is None
    assert user.list_preferences.await_args_list[1].kwargs["project_id"] == project_id


def test_transcript_dedup_keeps_structured_session_state() -> None:
    raw = _record(MemoryType.SESSION).model_copy(update={"content": "Q: explain RAG\nA: answer"})
    state = _record(MemoryType.SESSION).model_copy(
        update={"content": "Focus on latency", "metadata": {"kind": "active_goal"}}
    )
    deduplicated = MemoryService._deduplicate_session_history(
        [raw, state], "Q: explain RAG A: answer"
    )
    assert deduplicated == [state]
