"""
Canonical Prometheus collector registry (Prometheus Grafana Observability
PRD §12). One `CollectorRegistry` per process, created once and reused --
`get_counter`/`get_histogram`/`get_gauge` memoize by Prometheus metric
name so a metric already created is returned instead of re-registered
(the official client raises `ValueError` on duplicate registration).

Not a module-level singleton by itself (no side effects on import, PRD
§12 "avoid module-level registration side effects where possible") --
`app.ai.observability.prometheus.create.get_prometheus_metric_registry`
is what makes it one, and each test can construct its own instance for
isolation.
"""

from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram


class PrometheusMetricRegistry:
    def __init__(self, registry: CollectorRegistry | None = None) -> None:
        self._registry = registry or CollectorRegistry(auto_describe=True)
        self._counters: dict[str, Counter] = {}
        self._histograms: dict[str, Histogram] = {}
        self._gauges: dict[str, Gauge] = {}

    @property
    def registry(self) -> CollectorRegistry:
        return self._registry

    def get_counter(
        self,
        name: str,
        description: str,
        labels: tuple[str, ...] = (),
    ) -> Counter:
        existing = self._counters.get(name)
        if existing is not None:
            return existing

        counter = Counter(
            name,
            description,
            labelnames=labels,
            registry=self._registry,
        )
        self._counters[name] = counter
        return counter

    def get_histogram(
        self,
        name: str,
        description: str,
        labels: tuple[str, ...] = (),
        buckets: tuple[float, ...] | None = None,
    ) -> Histogram:
        existing = self._histograms.get(name)
        if existing is not None:
            return existing

        histogram = (
            Histogram(
                name,
                description,
                labelnames=labels,
                registry=self._registry,
                buckets=buckets,
            )
            if buckets is not None
            else Histogram(
                name,
                description,
                labelnames=labels,
                registry=self._registry,
            )
        )
        self._histograms[name] = histogram
        return histogram

    def get_gauge(
        self,
        name: str,
        description: str,
        labels: tuple[str, ...] = (),
    ) -> Gauge:
        existing = self._gauges.get(name)
        if existing is not None:
            return existing

        gauge = Gauge(
            name,
            description,
            labelnames=labels,
            registry=self._registry,
        )
        self._gauges[name] = gauge
        return gauge


__all__ = ["PrometheusMetricRegistry"]
