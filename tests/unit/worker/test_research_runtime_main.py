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
    # Never bind a real socket in a unit test -- this is a separate,
    # deliberate collaborator to stub, not something these two tests are
    # actually about (E17 follow-up, 2026-08-12).
    monkeypatch.setattr(research_runtime_main, "start_worker_metrics_server", lambda _port: None)

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
    # Never bind a real socket in a unit test -- this is a separate,
    # deliberate collaborator to stub, not something these two tests are
    # actually about (E17 follow-up, 2026-08-12).
    monkeypatch.setattr(research_runtime_main, "start_worker_metrics_server", lambda _port: None)

    created_workers: list[_FakeWorker] = []

    def fake_create_worker(*, session: object) -> _FakeWorker:
        worker = _FakeWorker()
        created_workers.append(worker)
        return worker

    monkeypatch.setattr(research_runtime_main, "create_research_runtime_worker", fake_create_worker)

    await research_runtime_main.main()

    assert len(created_workers) == 1
    created_workers[0].run.assert_awaited_once()


@pytest.mark.asyncio
async def test_main_starts_the_metrics_server_on_the_configured_port(monkeypatch) -> None:
    """E17 follow-up (2026-08-12): this worker has its own private
    Prometheus registry, invisible to the API's own `/metrics` -- see
    `start_worker_metrics_server()`'s own docstring for why."""

    monkeypatch.setattr(research_runtime_main.settings, "research_runtime_worker_concurrency", 1)
    monkeypatch.setattr(
        research_runtime_main.settings, "research_runtime_worker_metrics_port", 9999
    )

    @asynccontextmanager
    async def fake_session_factory():
        yield object()

    monkeypatch.setattr(research_runtime_main, "SessionFactory", lambda: fake_session_factory())
    monkeypatch.setattr(
        research_runtime_main, "create_research_runtime_worker", lambda **_: _FakeWorker()
    )

    calls: list[int] = []
    monkeypatch.setattr(
        research_runtime_main, "start_worker_metrics_server", lambda port: calls.append(port)
    )

    await research_runtime_main.main()

    assert calls == [9999]
