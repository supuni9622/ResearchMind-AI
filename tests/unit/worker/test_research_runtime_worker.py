from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from apps.worker.research_runtime_worker import ResearchRuntimeWorker


@pytest.mark.asyncio
async def test_worker_claims_executes_and_completes_an_approved_run() -> None:
    run_id = uuid4()
    dispatches = AsyncMock()
    dispatches.claim_next.return_value = SimpleNamespace(run_id=run_id, attempt_count=1)
    execute_run = AsyncMock()
    commit = AsyncMock()
    rollback = AsyncMock()
    worker = ResearchRuntimeWorker(
        dispatches=dispatches,
        execute_run=execute_run,
        commit=commit,
        rollback=rollback,
    )

    assert await worker.run_once() is True
    execute_run.assert_awaited_once_with(run_id)
    dispatches.complete.assert_awaited_once_with(run_id=run_id)
    assert commit.await_count == 2
    rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_worker_completes_outbox_after_execution_failure() -> None:
    run_id = uuid4()
    dispatches = AsyncMock()
    dispatches.claim_next.return_value = SimpleNamespace(run_id=run_id, attempt_count=1)
    execute_run = AsyncMock(side_effect=RuntimeError("provider unavailable"))
    commit = AsyncMock()
    rollback = AsyncMock()
    worker = ResearchRuntimeWorker(
        dispatches=dispatches,
        execute_run=execute_run,
        commit=commit,
        rollback=rollback,
    )

    assert await worker.run_once() is True
    dispatches.complete.assert_awaited_once_with(run_id=run_id)
    assert commit.await_count == 2


@pytest.mark.asyncio
async def test_worker_rolls_back_the_shared_session_after_a_failed_dispatch() -> None:
    """Regression test: this worker reuses one session for its whole process
    lifetime (see `research_runtime_main.py`), so a failure that aborts the
    session's transaction must be rolled back here -- otherwise every dispatch
    claimed afterward fails silently too, not just the one that errored."""

    run_id = uuid4()
    dispatches = AsyncMock()
    dispatches.claim_next.return_value = SimpleNamespace(run_id=run_id, attempt_count=1)
    execute_run = AsyncMock(side_effect=RuntimeError("transaction aborted"))
    commit = AsyncMock()
    rollback = AsyncMock()
    worker = ResearchRuntimeWorker(
        dispatches=dispatches,
        execute_run=execute_run,
        commit=commit,
        rollback=rollback,
    )

    assert await worker.run_once() is True
    rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_worker_returns_false_without_a_pending_dispatch() -> None:
    dispatches = AsyncMock()
    dispatches.claim_next.return_value = None
    worker = ResearchRuntimeWorker(
        dispatches=dispatches,
        execute_run=AsyncMock(),
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )

    assert await worker.run_once() is False
