"""
`MetricsRecorder` implementation backed by Prometheus (Prometheus
Grafana Observability PRD §13). Every business service already depends
only on `app.infrastructure.metrics.interfaces.MetricsRecorder` -- this
is the concrete adapter that turns those calls into real Prometheus
collectors, looked up centrally in `names.py` so a call site can never
create an unbounded-cardinality series by accident (PRD §13/§5.5).

Recording is best-effort throughout (PRD §5.4/§35): a failure here is
logged and swallowed, never raised, so Prometheus being unavailable or
misconfigured can never fail Chat, Research, Generation, Memory, Web
Search, MCP, or Guardrails.
"""

from __future__ import annotations

import structlog

from app.ai.observability.prometheus.names import (
    COUNTER_METRICS,
    DURATION_METRICS,
    GAUGE_METRICS,
    OBSERVE_METRICS,
    MetricSpec,
)
from app.ai.observability.prometheus.registry import PrometheusMetricRegistry
from app.infrastructure.metrics.interfaces import MetricsRecorder

logger = structlog.get_logger()

_UNKNOWN_LABEL_VALUE = "unknown"


def _resolve_labels(
    spec: MetricSpec,
    labels: dict[str, str] | None,
) -> dict[str, str]:
    """Filters to the metric's declared label schema and fills any
    missing declared label with 'unknown' -- PRD §15 "unsupported labels
    must be rejected or filtered", and every declared label must be
    present on every observation for Prometheus's client to accept it."""

    provided = labels or {}
    return {name: str(provided.get(name, _UNKNOWN_LABEL_VALUE)) for name in spec.labels}


class PrometheusMetricsRecorder(MetricsRecorder):
    def __init__(self, registry: PrometheusMetricRegistry) -> None:
        self._registry = registry

    def increment(
        self,
        *,
        metric: str,
        value: float = 1.0,
        labels: dict[str, str] | None = None,
    ) -> None:
        spec = COUNTER_METRICS.get(metric)
        if spec is None:
            logger.debug("prometheus.metric.unregistered", metric=metric, kind="counter")
            return

        try:
            counter = self._registry.get_counter(spec.name, spec.description, spec.labels)
            resolved = _resolve_labels(spec, labels)
            (counter.labels(**resolved) if resolved else counter).inc(value)
        except Exception as exc:
            logger.warning(
                "prometheus.metric.record_failed",
                metric=metric,
                error_type=type(exc).__name__,
            )

    def record_duration(
        self,
        *,
        operation: str,
        duration_ms: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        spec = DURATION_METRICS.get(operation)
        if spec is None:
            logger.debug("prometheus.metric.unregistered", metric=operation, kind="duration")
            return

        try:
            histogram = self._registry.get_histogram(
                spec.name, spec.description, spec.labels, spec.buckets
            )
            resolved = _resolve_labels(spec, labels)
            target = histogram.labels(**resolved) if resolved else histogram
            target.observe(duration_ms / 1000.0)
        except Exception as exc:
            logger.warning(
                "prometheus.metric.record_failed",
                metric=operation,
                error_type=type(exc).__name__,
            )

    def set_gauge(
        self,
        *,
        metric: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        spec = GAUGE_METRICS.get(metric)
        if spec is None:
            logger.debug("prometheus.metric.unregistered", metric=metric, kind="gauge")
            return

        try:
            gauge = self._registry.get_gauge(spec.name, spec.description, spec.labels)
            resolved = _resolve_labels(spec, labels)
            (gauge.labels(**resolved) if resolved else gauge).set(value)
        except Exception as exc:
            logger.warning(
                "prometheus.metric.record_failed",
                metric=metric,
                error_type=type(exc).__name__,
            )

    def observe(
        self,
        *,
        metric: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        spec = OBSERVE_METRICS.get(metric)
        if spec is None:
            logger.debug("prometheus.metric.unregistered", metric=metric, kind="observe")
            return

        try:
            histogram = self._registry.get_histogram(
                spec.name, spec.description, spec.labels, spec.buckets
            )
            resolved = _resolve_labels(spec, labels)
            (histogram.labels(**resolved) if resolved else histogram).observe(value)
        except Exception as exc:
            logger.warning(
                "prometheus.metric.record_failed",
                metric=metric,
                error_type=type(exc).__name__,
            )
