from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from app.ai.memory.enums import MemoryScopeType, MemoryType
from app.ai.memory.models import MemoryRecord, MemorySearchRequest
from app.ai.memory.services.memory_service import MemoryService


def _record(
    memory_type: MemoryType = MemoryType.USER,
    *,
    owner_id: UUID | None = None,
    scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
    project_id: UUID | None = None,
    content: str = "Prefer concise answers",
) -> MemoryRecord:
    now = datetime.now(UTC)
    return MemoryRecord(
        id=uuid4(),
        owner_id=owner_id or uuid4(),
        scope_type=scope_type,
        project_id=project_id,
        type=memory_type,
        content=content,
        metadata={"source": "extraction"},
        importance_score=0.8,
        created_at=now,
        updated_at=now,
    )


def _service(
    *,
    user: AsyncMock | None = None,
    semantic: AsyncMock | None = None,
    research: AsyncMock | None = None,
    settings_repository: AsyncMock | None = None,
    availability: AsyncMock | None = None,
) -> MemoryService:
    session = AsyncMock()
    session.recall.return_value = None
    resolved_user = user or AsyncMock()
    resolved_semantic = semantic or AsyncMock()
    resolved_research = research or AsyncMock()
    if user is None:
        resolved_user.recall.return_value = None
    if semantic is None:
        resolved_semantic.recall.return_value = None
    if research is None:
        resolved_research.recall.return_value = None
    return MemoryService(
        session_memory=session,
        user_memory=resolved_user,
        semantic_memory=resolved_semantic,
        research_memory=resolved_research,
        scope_settings=settings_repository,
        availability_service=availability,
    )


@pytest.mark.asyncio
async def test_disabled_capture_skips_automatic_extraction_without_deleting() -> None:
    settings_repository = AsyncMock()
    settings_repository.get.return_value = SimpleNamespace(
        capture_enabled=False, retrieval_enabled=True
    )
    user = AsyncMock()
    service = _service(user=user, settings_repository=settings_repository)

    record, outcome = await service.remember_extracted(
        owner_id=uuid4(),
        type=MemoryType.USER,
        content="Remember this preference",
        importance_score=0.9,
        metadata={"source": "extraction"},
    )

    assert record is None
    assert outcome == "capture_disabled"
    user.find_exact_content.assert_not_awaited()


@pytest.mark.asyncio
async def test_disabled_retrieval_returns_no_runtime_memory() -> None:
    settings_repository = AsyncMock()
    settings_repository.get.return_value = SimpleNamespace(
        capture_enabled=True, retrieval_enabled=False
    )
    user = AsyncMock()
    service = _service(user=user, settings_repository=settings_repository)

    result = await service.search(MemorySearchRequest(query="hello", owner_id=uuid4()))
    context = await service.get_context(owner_id=uuid4(), session_id=uuid4())

    assert result.memories == []
    assert context.model_dump() == {
        "session_memories": [],
        "user_memories": [],
        "semantic_memories": [],
        "research_memories": [],
    }
    user.list_preferences.assert_not_awaited()


@pytest.mark.asyncio
async def test_user_edit_records_explicit_provenance_and_reindexes_vector_memory() -> None:
    owner_id = uuid4()
    existing = _record(MemoryType.SEMANTIC, owner_id=owner_id)
    semantic = AsyncMock()
    semantic.recall.return_value = existing
    semantic.find_exact_content.return_value = None
    semantic.update.return_value = existing.model_copy(update={"content": "Edited fact"})
    availability = AsyncMock()
    service = _service(semantic=semantic, availability=availability)

    updated = await service.update_memory(
        owner_id=owner_id,
        memory_id=existing.id,
        type=MemoryType.SEMANTIC,
        content="Edited fact",
    )

    assert updated is not None
    metadata = semantic.update.await_args.kwargs["metadata"]
    assert metadata["source"] == "manual"
    assert metadata["origin"] == "explicit"
    assert len(metadata["_user_edit_history"]) == 1
    semantic.update.assert_awaited_once()
    availability.invalidate.assert_awaited_once()


@pytest.mark.asyncio
async def test_move_revalidates_destination_and_removes_source() -> None:
    owner_id = uuid4()
    project_id = uuid4()
    existing = _record(owner_id=owner_id)
    user = AsyncMock()
    user.recall.return_value = existing
    user.find_exact_content.return_value = None
    moved = existing.model_copy(
        update={
            "id": uuid4(),
            "scope_type": MemoryScopeType.PROJECT,
            "project_id": project_id,
        }
    )
    user.remember.return_value = moved
    user.forget.return_value = True
    service = _service(user=user)

    result = await service.move_memory(
        owner_id=owner_id,
        memory_id=existing.id,
        source_scope_type=MemoryScopeType.PERSONAL,
        source_project_id=None,
        destination_scope_type=MemoryScopeType.PROJECT,
        destination_project_id=project_id,
    )

    assert result == moved
    assert user.remember.await_args.kwargs["project_id"] == project_id
    assert user.remember.await_args.kwargs["metadata"]["_scope_move"]["confirmed"] is True
    user.forget.assert_awaited_once_with(
        owner_id=owner_id,
        memory_id=existing.id,
        scope_type=MemoryScopeType.PERSONAL,
        project_id=None,
    )
