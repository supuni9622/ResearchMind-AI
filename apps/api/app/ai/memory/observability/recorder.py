"""Structured-log metrics until the shared Prometheus backend is introduced."""

from __future__ import annotations

import structlog

from app.infrastructure.metrics.interfaces import MetricsRecorder

logger = structlog.get_logger()


class StructuredMemoryMetricsRecorder(MetricsRecorder):
    """Emit stable metric events without adding a memory-specific backend.

    The application-wide MetricsRecorder has no production sink yet. Logging
    these named counters/durations makes the memory rollout measurable now and
    keeps the call sites compatible with a later Prometheus implementation.
    """

    def record_duration(self, *, operation: str, duration_ms: float) -> None:
        logger.info(
            "memory.metric.duration",
            operation=operation,
            duration_ms=duration_ms,
        )

    def increment(self, *, metric: str) -> None:
        logger.info("memory.metric.increment", metric=metric)
