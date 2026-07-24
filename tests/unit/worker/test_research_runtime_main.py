from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest

from apps.worker import research_runtime_main


class _FakeWorker:
    def __init__(self) -> None:
        self.run = AsyncMock()
        self.stop = AsyncMock()


@pytest.mark.asyncio
async def test_main_runs_one_lane_per_configured_concurrency(monkeypatch) -> None:
    """REMAINING_WORK.md D2: `research_runtime_worker_concurrency` controls
    how many concurrent claim lanes (each its own DB session) this process
    runs -- the in-process half of fixing single-serial-worker throughput."""

    monkeypatch.setattr(research_runtime_main.settings, "research_runtime_worker_concurrency", 3)

    @asynccontextmanager
    async def fake_session_factory():
        yield object()

    monkeypatch.setattr(research_runtime_main, "SessionFactory", lambda: fake_session_factory())

    created_workers: list[_FakeWorker] = []

    def fake_create_worker(*, session: object) -> _FakeWorker:
        worker = _FakeWorker()
        created_workers.append(worker)
        return worker

    monkeypatch.setattr(research_runtime_main, "create_research_runtime_worker", fake_create_worker)

    await research_runtime_main.main()

    assert len(created_workers) == 3
    for worker in created_workers:
        worker.run.assert_awaited_once()


@pytest.mark.asyncio
async def test_main_defaults_to_a_single_lane_when_concurrency_is_unset(monkeypatch) -> None:
    monkeypatch.setattr(research_runtime_main.settings, "research_runtime_worker_concurrency", 1)

    @asynccontextmanager
    async def fake_session_factory():
        yield object()

    monkeypatch.setattr(research_runtime_main, "SessionFactory", lambda: fake_session_factory())

    created_workers: list[_FakeWorker] = []

    def fake_create_worker(*, session: object) -> _FakeWorker:
        worker = _FakeWorker()
        created_workers.append(worker)
        return worker

    monkeypatch.setattr(research_runtime_main, "create_research_runtime_worker", fake_create_worker)

    await research_runtime_main.main()

    assert len(created_workers) == 1
    created_workers[0].run.assert_awaited_once()
