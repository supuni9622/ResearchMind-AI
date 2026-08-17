from __future__ import annotations

from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.settings import Settings

from apps.worker.memory_lifecycle_worker import MemoryLifecycleWorker


def _settings() -> Settings:
    return cast(
        Settings,
        SimpleNamespace(
            memory_lifecycle_lock_ttl_seconds=60,
            memory_lifecycle_batch_size=25,
            memory_lifecycle_dry_run=True,
            memory_lifecycle_interval_seconds=60,
            memory_lifecycle_user_stale_after_days=365,
            memory_lifecycle_user_max_importance=0.1,
            memory_lifecycle_semantic_stale_after_days=90,
            memory_lifecycle_semantic_max_importance=0.3,
            memory_lifecycle_research_stale_after_days=180,
            memory_lifecycle_research_max_importance=0.2,
        ),
    )


@pytest.mark.asyncio
async def test_run_once_skips_when_another_worker_holds_lock() -> None:
    redis = MagicMock(set=AsyncMock(return_value=False), eval=AsyncMock())
    service = MagicMock(sweep_stale=AsyncMock())
    worker = MemoryLifecycleWorker(
        service=service, redis=redis, settings=_settings(), metrics=MagicMock()
    )

    assert await worker.run_once() is False
    service.sweep_stale.assert_not_awaited()
    redis.eval.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_once_applies_each_type_policy_and_releases_lock() -> None:
    redis = MagicMock(set=AsyncMock(return_value=True), eval=AsyncMock())
    service = MagicMock(sweep_stale=AsyncMock(return_value=0))
    metrics = MagicMock()
    worker = MemoryLifecycleWorker(
        service=service, redis=redis, settings=_settings(), metrics=metrics
    )

    assert await worker.run_once() is True
    assert service.sweep_stale.await_count == 3
    assert all(call.kwargs["dry_run"] is True for call in service.sweep_stale.await_args_list)
    redis.eval.assert_awaited_once()
    metrics.set_gauge.assert_called_once()


@pytest.mark.asyncio
async def test_lock_is_released_when_sweep_fails() -> None:
    redis = MagicMock(set=AsyncMock(return_value=True), eval=AsyncMock())
    service = MagicMock(sweep_stale=AsyncMock(side_effect=RuntimeError("db down")))
    worker = MemoryLifecycleWorker(
        service=service, redis=redis, settings=_settings(), metrics=MagicMock()
    )

    with pytest.raises(RuntimeError, match="db down"):
        await worker.run_once()

    redis.eval.assert_awaited_once()
