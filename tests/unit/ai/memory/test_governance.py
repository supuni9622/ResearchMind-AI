from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.ai.memory.governance import MemoryGovernanceService
from app.infrastructure.metrics.noop import NoOpMetricsRecorder
from app.models.memory import MemoryDeletionConfirmation, MemoryGovernanceJob


class _Scalars:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def all(self) -> list[object]:
        return self._values


class _Result:
    def __init__(self, values: list[object] | None = None, rowcount: int = 0) -> None:
        self._values = values or []
        self.rowcount = rowcount

    def scalars(self) -> _Scalars:
        return _Scalars(self._values)


def _job_and_confirmation() -> tuple[MemoryGovernanceJob, MemoryDeletionConfirmation]:
    owner_id = uuid4()
    confirmation = MemoryDeletionConfirmation(
        id=uuid4(),
        owner_id=owner_id,
        token_hash="hash",
        scope_type="personal",
        project_id=None,
        memory_ids=None,
        expected_count=1,
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    job = MemoryGovernanceJob(
        id=uuid4(),
        owner_id=owner_id,
        confirmation_id=confirmation.id,
        scope_type="personal",
        project_id=None,
        status="running",
        requested_count=1,
        deleted_postgres=0,
        deleted_qdrant=0,
        deleted_valkey=0,
        deleted_artifacts=0,
    )
    return job, confirmation


@pytest.mark.asyncio
async def test_erasure_stops_before_canonical_delete_when_vector_delete_fails() -> None:
    job, confirmation = _job_and_confirmation()
    memory_id = uuid4()
    session = AsyncMock()
    session.execute.return_value = _Result([SimpleNamespace(id=memory_id, type="semantic")])
    vector_index = AsyncMock()
    vector_index.delete.return_value = False
    service = MemoryGovernanceService(
        session,
        vector_index,
        AsyncMock(),
        AsyncMock(),
        NoOpMetricsRecorder(),
    )

    result = await service._run(job, confirmation)

    assert result.status == "failed"
    assert result.failure_stage == "qdrant"
    assert session.execute.await_count == 1
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_failed_cross_store_erasure_converges_when_retried() -> None:
    job, confirmation = _job_and_confirmation()
    memory_id = uuid4()
    session = AsyncMock()
    session.execute.side_effect = [
        _Result([SimpleNamespace(id=memory_id, type="semantic")]),
        _Result([SimpleNamespace(id=memory_id, type="semantic")]),
        _Result(rowcount=1),
        _Result([]),
    ]
    vector_index = AsyncMock()
    vector_index.delete.side_effect = [False, True]
    session_store = AsyncMock()
    session_store.purge_scope.return_value = 2
    artifacts = AsyncMock()
    artifacts.purge_scope.return_value = 1
    service = MemoryGovernanceService(
        session,
        vector_index,
        session_store,
        artifacts,
        NoOpMetricsRecorder(),
    )

    first = await service._run(job, confirmation)
    assert first.status == "failed"
    assert first.failure_stage == "qdrant"

    job.status = "running"
    job.failure_stage = None
    job.failure_detail = None
    second = await service._run(job, confirmation)

    assert second.status == "completed"
    assert second.deleted_postgres == 1
    assert second.deleted_qdrant == 1
    assert second.deleted_valkey == 2
    assert second.deleted_artifacts == 1
