"""
Fans a single `MetricsRecorder` call out to several backends (Prometheus
Grafana Observability PRD §5.4/§35 "Failure Handling"). Lets a platform
keep its existing recorder (e.g. Memory's structured-log recorder) while
also feeding the new Prometheus recorder, without either call site
knowing about the other. Each backend is isolated in its own try/except
-- one backend raising never stops the others from recording, and never
propagates to the caller.
"""

from __future__ import annotations

from collections.abc import Sequence

import structlog
from app.infrastructure.metrics.interfaces import MetricsRecorder

logger = structlog.get_logger()


class CompositeMetricsRecorder(MetricsRecorder):
    def __init__(self, recorders: Sequence[MetricsRecorder]) -> None:
        self._recorders = list(recorders)

    def record_duration(
        self,
        *,
        operation: str,
        duration_ms: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        for recorder in self._recorders:
            try:
                recorder.record_duration(
                    operation=operation,
                    duration_ms=duration_ms,
                    labels=labels,
                )
            except Exception as exc:
                logger.warning(
                    "metrics.composite.record_duration_failed",
                    operation=operation,
                    recorder=type(recorder).__name__,
                    error_type=type(exc).__name__,
                )

    def increment(
        self,
        *,
        metric: str,
        value: float = 1.0,
        labels: dict[str, str] | None = None,
    ) -> None:
        for recorder in self._recorders:
            try:
                recorder.increment(metric=metric, value=value, labels=labels)
            except Exception as exc:
                logger.warning(
                    "metrics.composite.increment_failed",
                    metric=metric,
                    recorder=type(recorder).__name__,
                    error_type=type(exc).__name__,
                )

    def set_gauge(
        self,
        *,
        metric: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        for recorder in self._recorders:
            try:
                recorder.set_gauge(metric=metric, value=value, labels=labels)
            except Exception as exc:
                logger.warning(
                    "metrics.composite.set_gauge_failed",
                    metric=metric,
                    recorder=type(recorder).__name__,
                    error_type=type(exc).__name__,
                )

    def observe(
        self,
        *,
        metric: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        for recorder in self._recorders:
            try:
                recorder.observe(metric=metric, value=value, labels=labels)
            except Exception as exc:
                logger.warning(
                    "metrics.composite.observe_failed",
                    metric=metric,
                    recorder=type(recorder).__name__,
                    error_type=type(exc).__name__,
                )
