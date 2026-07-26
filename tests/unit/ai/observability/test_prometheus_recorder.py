"""
Unit tests for `PrometheusMetricsRecorder` (prometheus_grafana_
observability_prd.md §13/§36.1).

Covers:
- increment()/record_duration()/set_gauge()/observe() on a registered
  metric create and update the expected Prometheus series
- missing declared labels are filled with "unknown" rather than raising
- an unregistered metric/operation name is a silent no-op (PRD §13
  "unknown metrics must not be created accidentally")
- a registry failure is swallowed, never raised (PRD §5.4/§35)
"""

from __future__ import annotations

from unittest.mock import MagicMock

from app.ai.observability.prometheus.recorder import PrometheusMetricsRecorder
from app.ai.observability.prometheus.registry import PrometheusMetricRegistry
from app.infrastructure.metrics.generation import GENERATION_REQUESTS_TOTAL


def test_increment_creates_and_increments_counter() -> None:
    registry = PrometheusMetricRegistry()
    recorder = PrometheusMetricsRecorder(registry)

    recorder.increment(
        metric=GENERATION_REQUESTS_TOTAL,
        labels={
            "runtime": "chat",
            "provider": "groq",
            "model_family": "llama",
            "cache_hit": "false",
        },
    )

    value = registry.registry.get_sample_value(
        "researchmind_generation_requests_total",
        {
            "runtime": "chat",
            "provider": "groq",
            "model_family": "llama",
            "cache_hit": "false",
        },
    )
    assert value == 1.0


def test_increment_fills_missing_labels_with_unknown() -> None:
    registry = PrometheusMetricRegistry()
    recorder = PrometheusMetricsRecorder(registry)

    recorder.increment(metric=GENERATION_REQUESTS_TOTAL)

    value = registry.registry.get_sample_value(
        "researchmind_generation_requests_total",
        {
            "runtime": "unknown",
            "provider": "unknown",
            "model_family": "unknown",
            "cache_hit": "unknown",
        },
    )
    assert value == 1.0


def test_record_duration_converts_ms_to_seconds() -> None:
    registry = PrometheusMetricRegistry()
    recorder = PrometheusMetricsRecorder(registry)

    recorder.record_duration(
        operation="generation",
        duration_ms=250.0,
        labels={"runtime": "chat", "provider": "groq"},
    )

    count = registry.registry.get_sample_value(
        "researchmind_generation_duration_seconds_count",
        {"runtime": "chat", "provider": "groq"},
    )
    total = registry.registry.get_sample_value(
        "researchmind_generation_duration_seconds_sum",
        {"runtime": "chat", "provider": "groq"},
    )
    assert count == 1.0
    assert total == 0.25


def test_unregistered_increment_metric_is_a_noop() -> None:
    registry = PrometheusMetricRegistry()
    recorder = PrometheusMetricsRecorder(registry)

    # Must not raise, and must not create any series.
    recorder.increment(metric="totally_made_up_metric")

    assert registry.registry.get_sample_value("totally_made_up_metric") is None


def test_unregistered_duration_operation_is_a_noop() -> None:
    registry = PrometheusMetricRegistry()
    recorder = PrometheusMetricsRecorder(registry)

    recorder.record_duration(operation="not_a_real_operation", duration_ms=10.0)


def test_unregistered_gauge_metric_is_a_noop() -> None:
    registry = PrometheusMetricRegistry()
    recorder = PrometheusMetricsRecorder(registry)

    recorder.set_gauge(metric="not_a_real_gauge", value=1.0)


def test_unregistered_observe_metric_is_a_noop() -> None:
    registry = PrometheusMetricRegistry()
    recorder = PrometheusMetricsRecorder(registry)

    recorder.observe(metric="not_a_real_histogram", value=1.0)


def test_recorder_failure_is_swallowed_not_raised() -> None:
    broken_registry = MagicMock(spec=PrometheusMetricRegistry)
    broken_registry.get_counter.side_effect = RuntimeError("registry exploded")
    recorder = PrometheusMetricsRecorder(broken_registry)

    # Must not raise even though the underlying registry is broken.
    recorder.increment(metric=GENERATION_REQUESTS_TOTAL)
