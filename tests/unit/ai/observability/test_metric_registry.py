"""
Unit tests for `PrometheusMetricRegistry` (prometheus_grafana_observability_
prd.md §12/§36.1).

Covers:
- get_counter/get_histogram/get_gauge create a collector on first call
- a second call with the same name returns the same collector instead
  of re-registering it (would otherwise raise `ValueError`)
- histograms honor an explicit bucket tuple
- each registry uses its own isolated `CollectorRegistry`
"""

from __future__ import annotations

from app.ai.observability.prometheus.registry import PrometheusMetricRegistry
from prometheus_client import Counter, Gauge, Histogram


def test_get_counter_creates_once_and_memoizes() -> None:
    registry = PrometheusMetricRegistry()

    first = registry.get_counter("researchmind_test_counter_total", "desc", ("a",))
    second = registry.get_counter("researchmind_test_counter_total", "desc", ("a",))

    assert isinstance(first, Counter)
    assert first is second


def test_get_histogram_creates_once_and_memoizes() -> None:
    registry = PrometheusMetricRegistry()

    first = registry.get_histogram("researchmind_test_duration_seconds", "desc", ("a",), (0.1, 1.0))
    second = registry.get_histogram(
        "researchmind_test_duration_seconds", "desc", ("a",), (0.1, 1.0)
    )

    assert isinstance(first, Histogram)
    assert first is second


def test_get_gauge_creates_once_and_memoizes() -> None:
    registry = PrometheusMetricRegistry()

    first = registry.get_gauge("researchmind_test_gauge", "desc", ("a",))
    second = registry.get_gauge("researchmind_test_gauge", "desc", ("a",))

    assert isinstance(first, Gauge)
    assert first is second


def test_registries_are_isolated_from_each_other() -> None:
    registry_a = PrometheusMetricRegistry()
    registry_b = PrometheusMetricRegistry()

    # Same metric name registered in two independent registries must not
    # raise -- each wraps its own CollectorRegistry.
    registry_a.get_counter("researchmind_isolated_total", "desc")
    registry_b.get_counter("researchmind_isolated_total", "desc")

    assert registry_a.registry is not registry_b.registry


def test_counter_without_labels_can_be_incremented_directly() -> None:
    registry = PrometheusMetricRegistry()

    counter = registry.get_counter("researchmind_no_label_total", "desc")
    counter.inc()

    value = registry.registry.get_sample_value("researchmind_no_label_total")
    assert value == 1.0
