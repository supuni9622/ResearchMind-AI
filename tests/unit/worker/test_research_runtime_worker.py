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


@pytest.mark.asyncio
async def test_expire_sweep_is_a_no_op_when_not_configured() -> None:
    worker = ResearchRuntimeWorker(
        dispatches=AsyncMock(),
        execute_run=AsyncMock(),
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )

    await worker._maybe_expire_stale_awaiting_approval()


@pytest.mark.asyncio
async def test_expire_sweep_runs_once_when_configured_and_due() -> None:
    expire = AsyncMock(return_value=2)
    worker = ResearchRuntimeWorker(
        dispatches=AsyncMock(),
        execute_run=AsyncMock(),
        commit=AsyncMock(),
        rollback=AsyncMock(),
        expire_stale_awaiting_approval=expire,
    )

    await worker._maybe_expire_stale_awaiting_approval()

    expire.assert_awaited_once()


@pytest.mark.asyncio
async def test_expire_sweep_skips_a_second_call_within_the_interval() -> None:
    expire = AsyncMock(return_value=0)
    worker = ResearchRuntimeWorker(
        dispatches=AsyncMock(),
        execute_run=AsyncMock(),
        commit=AsyncMock(),
        rollback=AsyncMock(),
        expire_stale_awaiting_approval=expire,
        expire_interval_seconds=3600.0,
    )

    await worker._maybe_expire_stale_awaiting_approval()
    await worker._maybe_expire_stale_awaiting_approval()

    expire.assert_awaited_once()


@pytest.mark.asyncio
async def test_expire_sweep_runs_again_once_the_interval_elapses() -> None:
    expire = AsyncMock(return_value=0)
    worker = ResearchRuntimeWorker(
        dispatches=AsyncMock(),
        execute_run=AsyncMock(),
        commit=AsyncMock(),
        rollback=AsyncMock(),
        expire_stale_awaiting_approval=expire,
        expire_interval_seconds=0.0,
    )

    await worker._maybe_expire_stale_awaiting_approval()
    await worker._maybe_expire_stale_awaiting_approval()

    assert expire.await_count == 2


@pytest.mark.asyncio
async def test_expire_sweep_rolls_back_the_shared_session_on_failure() -> None:
    """Regression test: mirrors the dispatch-failure rollback -- this worker
    holds one session for its entire process lifetime, so a sweep failure
    left unrolled-back would poison every dispatch claimed afterward."""

    expire = AsyncMock(side_effect=RuntimeError("db unavailable"))
    rollback = AsyncMock()
    worker = ResearchRuntimeWorker(
        dispatches=AsyncMock(),
        execute_run=AsyncMock(),
        commit=AsyncMock(),
        rollback=rollback,
        expire_stale_awaiting_approval=expire,
    )

    await worker._maybe_expire_stale_awaiting_approval()

    rollback.assert_awaited_once()
