"""Low-frequency, bounded-cardinality durable-memory inventory metrics."""

from __future__ import annotations

import time

from app.ai.memory.observability import metrics
from app.ai.memory.storage.vector_index import MemoryVectorIndex
from app.infrastructure.metrics.interfaces import MetricsRecorder
from app.repositories.memory import MemoryRepository


class MemoryInventoryMetricsService:
    def __init__(
        self,
        repository: MemoryRepository,
        vector_index: MemoryVectorIndex,
        metrics_recorder: MetricsRecorder,
    ) -> None:
        self._repository = repository
        self._vector_index = vector_index
        self._metrics = metrics_recorder

    async def collect(self) -> None:
        snapshot = await self._repository.memory_observability_snapshot()
        for (memory_type, scope), row_count in snapshot["counts"].items():
            self._metrics.set_gauge(
                metric=metrics.STORAGE_ROWS,
                value=float(row_count),
                labels={"type": memory_type, "scope": scope},
            )
        for memory_type, oldest_age in snapshot["oldest_age_seconds"].items():
            self._metrics.set_gauge(
                metric=metrics.STORAGE_OLDEST_AGE,
                value=oldest_age,
                labels={"type": memory_type},
            )
        for kind, byte_count in snapshot["sizes"].items():
            self._metrics.set_gauge(
                metric=metrics.STORAGE_BYTES,
                value=float(byte_count),
                labels={"kind": kind},
            )
        for (dimension, quantile), distribution_value in snapshot["distributions"].items():
            self._metrics.set_gauge(
                metric=metrics.STORAGE_DISTRIBUTION,
                value=distribution_value,
                labels={"dimension": dimension, "quantile": quantile},
            )

        postgres_ids = await self._repository.list_vector_memory_ids()
        qdrant_ids = await self._vector_index.list_point_ids()
        self._metrics.set_gauge(metric=metrics.VECTOR_POINTS, value=float(len(qdrant_ids)))
        self._metrics.set_gauge(
            metric=metrics.VECTOR_DRIFT,
            value=float(len(postgres_ids - qdrant_ids)),
            labels={"kind": "missing_point"},
        )
        self._metrics.set_gauge(
            metric=metrics.VECTOR_DRIFT,
            value=float(len(qdrant_ids - postgres_ids)),
            labels={"kind": "orphan_point"},
        )
        self._metrics.set_gauge(metric=metrics.INVENTORY_LAST_SUCCESS, value=time.time())
