from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.ai.memory.enums import MemoryType
from app.ai.memory.lifecycle.service import MemoryLifecycleService


def _row(memory_type: MemoryType) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        type=memory_type.value,
        updated_at=datetime.now(UTC) - timedelta(days=200),
    )


@pytest.mark.asyncio
async def test_dry_run_reports_candidates_without_mutating_storage() -> None:
    repository = MagicMock()
    repository.list_stale = AsyncMock(return_value=[_row(MemoryType.USER)])
    repository.delete = AsyncMock()
    repository.session = MagicMock(commit=AsyncMock(), rollback=AsyncMock())
    vector = MagicMock(delete=AsyncMock())

    count = await MemoryLifecycleService(repository, vector).sweep_stale(
        memory_types=(MemoryType.USER,), dry_run=True, batch_size=10
    )

    assert count == 1
    repository.delete.assert_not_awaited()
    vector.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_vector_failure_preserves_canonical_row_and_continues() -> None:
    semantic = _row(MemoryType.SEMANTIC)
    user = _row(MemoryType.USER)
    repository = MagicMock()
    repository.list_stale = AsyncMock(return_value=[semantic, user])
    repository.delete = AsyncMock()
    repository.session = MagicMock(commit=AsyncMock(), rollback=AsyncMock())
    vector = MagicMock(delete=AsyncMock(return_value=False))

    count = await MemoryLifecycleService(repository, vector).sweep_stale()

    assert count == 1
    repository.delete.assert_awaited_once_with(user)
    repository.session.rollback.assert_awaited_once()
    repository.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_batch_and_type_policy_are_forwarded_to_repository() -> None:
    repository = MagicMock()
    repository.list_stale = AsyncMock(return_value=[])
    repository.session = MagicMock(commit=AsyncMock(), rollback=AsyncMock())

    await MemoryLifecycleService(repository, MagicMock()).sweep_stale(
        stale_after_days=30,
        max_importance=0.2,
        memory_types=(MemoryType.RESEARCH,),
        batch_size=25,
    )

    kwargs = repository.list_stale.await_args.kwargs
    assert kwargs["types"] == [MemoryType.RESEARCH.value]
    assert kwargs["limit"] == 25
    assert kwargs["max_importance"] == 0.2
