"""Owner-scoped, fail-open durable-memory availability checks."""

from __future__ import annotations

from uuid import UUID

import structlog
from redis.asyncio import Redis

from app.ai.memory.enums import MemoryType
from app.ai.memory.storage.postgres_store import PostgresMemoryStore
from app.core.settings import settings
from app.infrastructure.metrics.interfaces import MetricsRecorder
from app.infrastructure.metrics.noop import NoOpMetricsRecorder

logger = structlog.get_logger()

_DURABLE_TYPES = {MemoryType.SEMANTIC, MemoryType.RESEARCH}


class DurableMemoryAvailabilityService:
    def __init__(
        self,
        store: PostgresMemoryStore,
        client: Redis | None = None,
        metrics: MetricsRecorder | None = None,
    ) -> None:
        self._store = store
        self._client = client
        self._metrics = metrics or NoOpMetricsRecorder()

    async def has_durable_memory(self, *, owner_id: UUID) -> bool:
        key = self._key(owner_id)
        if settings.memory_durable_availability_cache_enabled and self._client is not None:
            try:
                cached = await self._client.get(key)
                if cached is not None:
                    return str(cached) == "1"
            except Exception:
                logger.warning("memory.availability.cache_read_failed", owner_id=str(owner_id))

        try:
            available = await self._store.exists_for_owner(
                owner_id=owner_id,
                memory_types=_DURABLE_TYPES,
            )
        except Exception as exc:
            # An unavailable availability store must not hide Session memory
            # or stop the user request. Treat it as "unknown" and allow the
            # caller to attempt best-effort vector retrieval.
            logger.warning(
                "memory.availability.store_check_failed",
                owner_id=str(owner_id),
                error_type=type(exc).__name__,
                error=str(exc),
            )
            return True
        if settings.memory_durable_availability_cache_enabled and self._client is not None:
            try:
                await self._client.set(
                    key,
                    "1" if available else "0",
                    ex=settings.memory_durable_availability_ttl_seconds,
                )
            except Exception:
                logger.warning("memory.availability.cache_write_failed", owner_id=str(owner_id))
        return available

    async def invalidate(self, *, owner_id: UUID) -> None:
        if self._client is None:
            return
        try:
            await self._client.delete(self._key(owner_id))
        except Exception:
            logger.warning("memory.availability.cache_invalidate_failed", owner_id=str(owner_id))

    @staticmethod
    def _key(owner_id: UUID) -> str:
        return f"memory:durable-exists:{owner_id}"
