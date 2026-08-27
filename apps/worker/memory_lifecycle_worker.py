"""Recurring, singleton runner for bounded durable-memory lifecycle sweeps."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable
from contextlib import suppress
from typing import cast
from uuid import uuid4

import structlog
from app.ai.memory.consolidation.service import MemoryConsolidationService
from app.ai.memory.enums import MemoryType
from app.ai.memory.lifecycle.service import MemoryLifecycleService
from app.ai.memory.observability import metrics as memory_metrics
from app.ai.memory.observability.inventory import MemoryInventoryMetricsService
from app.core.settings import Settings
from app.infrastructure.metrics.interfaces import MetricsRecorder
from redis.asyncio import Redis

logger = structlog.get_logger()

_LOCK_KEY = "memory:lifecycle:singleton"
_RELEASE_LOCK = """
if redis.call('get', KEYS[1]) == ARGV[1] then
  return redis.call('del', KEYS[1])
end
return 0
"""


class MemoryLifecycleWorker:
    def __init__(
        self,
        *,
        service: MemoryLifecycleService,
        redis: Redis,
        settings: Settings,
        metrics: MetricsRecorder,
        consolidation_service: MemoryConsolidationService | None = None,
        inventory_metrics_service: MemoryInventoryMetricsService | None = None,
    ) -> None:
        self._service = service
        self._redis = redis
        self._settings = settings
        self._metrics = metrics
        self._consolidation_service = consolidation_service
        self._inventory_metrics_service = inventory_metrics_service
        self._stopping = False
        self._stop_event = asyncio.Event()

    def stop(self) -> None:
        self._stopping = True
        self._stop_event.set()

    async def run_once(self) -> bool:
        token = str(uuid4())
        acquired = await self._redis.set(
            _LOCK_KEY,
            token,
            ex=self._settings.memory_lifecycle_lock_ttl_seconds,
            nx=True,
        )
        if not acquired:
            logger.info("memory.lifecycle.lock_contended")
            return False

        started = time.perf_counter()
        try:
            policies = (
                (
                    MemoryType.USER,
                    self._settings.memory_lifecycle_user_stale_after_days,
                    self._settings.memory_lifecycle_user_max_importance,
                ),
                (
                    MemoryType.SEMANTIC,
                    self._settings.memory_lifecycle_semantic_stale_after_days,
                    self._settings.memory_lifecycle_semantic_max_importance,
                ),
                (
                    MemoryType.RESEARCH,
                    self._settings.memory_lifecycle_research_stale_after_days,
                    self._settings.memory_lifecycle_research_max_importance,
                ),
            )
            for memory_type, stale_days, max_importance in policies:
                await self._service.sweep_stale(
                    stale_after_days=stale_days,
                    max_importance=max_importance,
                    memory_types=(memory_type,),
                    batch_size=self._settings.memory_lifecycle_batch_size,
                    dry_run=self._settings.memory_lifecycle_dry_run,
                )
            if (
                self._consolidation_service is not None
                and self._settings.memory_consolidation_enabled
            ):
                consolidation_started = time.perf_counter()
                await self._consolidation_service.run_batch(
                    batch_size=self._settings.memory_consolidation_batch_size,
                    candidate_limit=self._settings.memory_consolidation_candidate_limit,
                    similarity_threshold=(self._settings.memory_consolidation_similarity_threshold),
                    dry_run=self._settings.memory_consolidation_dry_run,
                )
                self._metrics.record_duration(
                    operation=memory_metrics.CONSOLIDATION_DURATION,
                    duration_ms=(time.perf_counter() - consolidation_started) * 1000,
                )
            if self._inventory_metrics_service is not None:
                try:
                    await self._inventory_metrics_service.collect()
                except Exception as exc:
                    logger.exception(
                        "memory.inventory.collection_failed",
                        error_type=type(exc).__name__,
                    )
            self._metrics.set_gauge(
                metric=memory_metrics.LIFECYCLE_LAST_SUCCESS,
                value=time.time(),
            )
            return True
        finally:
            self._metrics.record_duration(
                operation=memory_metrics.LIFECYCLE_DURATION,
                duration_ms=(time.perf_counter() - started) * 1000,
            )
            await cast(
                Awaitable[object],
                self._redis.eval(_RELEASE_LOCK, 1, _LOCK_KEY, token),
            )

    async def run(self) -> None:
        while not self._stopping:
            try:
                await self.run_once()
            except Exception:
                logger.exception("memory.lifecycle.run_failed")
            if not self._stopping:
                with suppress(TimeoutError):
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=self._settings.memory_lifecycle_interval_seconds,
                    )
