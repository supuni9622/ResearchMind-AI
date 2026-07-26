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

    def record_duration(
        self,
        *,
        operation: str,
        duration_ms: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        logger.info(
            "memory.metric.duration",
            operation=operation,
            duration_ms=duration_ms,
            labels=labels,
        )

    def increment(
        self,
        *,
        metric: str,
        value: float = 1.0,
        labels: dict[str, str] | None = None,
    ) -> None:
        logger.info("memory.metric.increment", metric=metric, value=value, labels=labels)

    def set_gauge(
        self,
        *,
        metric: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        logger.info("memory.metric.gauge", metric=metric, value=value, labels=labels)

    def observe(
        self,
        *,
        metric: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        logger.info("memory.metric.observe", metric=metric, value=value, labels=labels)
