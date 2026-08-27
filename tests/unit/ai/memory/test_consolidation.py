from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.ai.memory.consolidation.models import (
    ConsolidationAction,
    ConsolidationDecision,
)
from app.ai.memory.consolidation.service import MemoryConsolidationService
from app.ai.memory.enums import MemoryType
from app.models.memory import Memory


def _row(content: str, *, age_minutes: int = 0, owner_id=None) -> Memory:
    now = datetime.now(UTC) - timedelta(minutes=age_minutes)
    return Memory(
        id=uuid4(),
        owner_id=owner_id or uuid4(),
        scope_type="personal",
        project_id=None,
        type=MemoryType.SEMANTIC.value,
        content=content,
        memory_metadata={"source": "test"},
        importance_score=0.5,
        created_at=now,
        updated_at=now,
    )


def _service(seed: Memory, candidate: Memory, decision: ConsolidationDecision):
    session = MagicMock(commit=AsyncMock(), rollback=AsyncMock())
    repository = MagicMock(session=session)
    repository.list_consolidation_seeds = AsyncMock(return_value=[seed])
    repository.get_by_id_for_owner = AsyncMock(return_value=candidate)
    index = MagicMock()
    index.search = AsyncMock(return_value=[seed.id, candidate.id])
    index.upsert = AsyncMock(return_value=True)
    index.delete = AsyncMock(return_value=True)
    embeddings = MagicMock(embed=AsyncMock(return_value=[0.1, 0.2]))
    decisions = MagicMock(decide=AsyncMock(return_value=decision))
    return (
        MemoryConsolidationService(repository, index, embeddings, decisions),
        repository,
        index,
    )


@pytest.mark.asyncio
async def test_dry_run_classifies_without_mutating_rows() -> None:
    owner_id = uuid4()
    seed = _row("RAG uses retrieval.", owner_id=owner_id)
    candidate = _row("Retrieval is used by RAG.", age_minutes=5, owner_id=owner_id)
    service, repository, index = _service(
        seed,
        candidate,
        ConsolidationDecision(
            action=ConsolidationAction.DUPLICATE,
            merged_content="",
            reason="same fact",
        ),
    )

    result = await service.run_batch(dry_run=True)

    assert result.candidates == 1
    assert result.duplicates == 1
    repository.session.commit.assert_not_awaited()
    index.upsert.assert_not_awaited()
    index.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_merge_preserves_source_as_reversible_lineage() -> None:
    owner_id = uuid4()
    canonical = _row("RAG retrieves context.", age_minutes=10, owner_id=owner_id)
    source = _row("RAG supplies context to generation.", owner_id=owner_id)
    service, repository, index = _service(
        source,
        canonical,
        ConsolidationDecision(
            action=ConsolidationAction.MERGEABLE,
            merged_content="RAG retrieves and supplies context to generation.",
            reason="compatible",
        ),
    )

    result = await service.run_batch(dry_run=False)

    assert result.merged == 1
    assert canonical.content == "RAG retrieves and supplies context to generation."
    assert canonical.memory_metadata["_merged_from"] == [str(source.id)]
    assert source.memory_metadata["_consolidated_into"] == str(canonical.id)
    index.upsert.assert_awaited_once()
    index.delete.assert_awaited_once_with(source.id)
    repository.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_contradiction_is_retained_and_only_marked_reviewed() -> None:
    owner_id = uuid4()
    seed = _row("The result was positive.", owner_id=owner_id)
    candidate = _row("The result was negative.", age_minutes=5, owner_id=owner_id)
    service, repository, index = _service(
        seed,
        candidate,
        ConsolidationDecision(
            action=ConsolidationAction.CONTRADICTION,
            merged_content="",
            reason="conflicting evidence",
        ),
    )

    result = await service.run_batch(dry_run=False)

    assert result.contradictions == 1
    assert "_consolidated_into" not in seed.memory_metadata
    assert seed.memory_metadata["_consolidation_last_outcome"] == "contradiction"
    index.upsert.assert_not_awaited()
    index.delete.assert_not_awaited()
    repository.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_vector_failure_leaves_postgres_lineage_unchanged() -> None:
    owner_id = uuid4()
    canonical = _row("same", age_minutes=10, owner_id=owner_id)
    source = _row("same fact", owner_id=owner_id)
    service, repository, index = _service(
        source,
        canonical,
        ConsolidationDecision(
            action=ConsolidationAction.DUPLICATE,
            merged_content="",
            reason="duplicate",
        ),
    )
    index.delete.return_value = False

    result = await service.run_batch(dry_run=False)

    assert result.failed == 1
    assert "_consolidated_into" not in source.memory_metadata
    repository.session.commit.assert_not_awaited()
    repository.session.rollback.assert_awaited_once()
