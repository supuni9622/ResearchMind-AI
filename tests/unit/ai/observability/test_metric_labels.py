"""
Unit tests enforcing the Prometheus Grafana Observability PRD's naming
and label-cardinality policy (§14/§15) across every metric declared in
`app.ai.observability.prometheus.names`.

Covers:
- every metric name carries the `researchmind_` prefix
- counters end in `_total`
- gauges never end in `_total`
- histograms declare bucket boundaries
- no forbidden (unbounded/PII) label ever appears on any metric
- `normalize_model_family` only ever returns a bounded value
"""

from __future__ import annotations

from app.ai.observability.prometheus.labels import normalize_model_family
from app.ai.observability.prometheus.names import (
    COUNTER_METRICS,
    DURATION_METRICS,
    GAUGE_METRICS,
    OBSERVE_METRICS,
)

_FORBIDDEN_LABELS = {
    "owner_id",
    "user_id",
    "workspace_id",
    "session_id",
    "conversation_id",
    "research_id",
    "request_id",
    "correlation_id",
    "document_id",
    "citation_id",
    "artifact_id",
    "query",
    "prompt",
    "url",
    "exception_message",
    "email",
    "access_token",
    "api_key",
}

_ALL_SPECS = {
    **COUNTER_METRICS,
    **DURATION_METRICS,
    **GAUGE_METRICS,
    **OBSERVE_METRICS,
}


def test_every_metric_name_has_the_researchmind_prefix() -> None:
    for spec in _ALL_SPECS.values():
        assert spec.name.startswith("researchmind_"), spec.name


def test_every_counter_ends_in_total() -> None:
    for spec in COUNTER_METRICS.values():
        assert spec.name.endswith("_total"), spec.name
        assert spec.kind == "counter"


def test_gauges_never_end_in_total() -> None:
    for spec in GAUGE_METRICS.values():
        assert not spec.name.endswith("_total"), spec.name
        assert spec.kind == "gauge"


def test_every_histogram_declares_buckets() -> None:
    for spec in {**DURATION_METRICS, **OBSERVE_METRICS}.values():
        assert spec.kind == "histogram"
        assert spec.buckets is not None
        assert len(spec.buckets) > 0


def test_no_metric_declares_a_forbidden_label() -> None:
    for spec in _ALL_SPECS.values():
        for label in spec.labels:
            assert label not in _FORBIDDEN_LABELS, f"{spec.name} declares forbidden label {label}"


def test_no_duplicate_prometheus_metric_names_across_kinds() -> None:
    names = [spec.name for spec in _ALL_SPECS.values()]
    assert len(names) == len(set(names))


def test_normalize_model_family_is_bounded() -> None:
    bounded = {"gpt", "claude", "gemini", "llama", "deepseek", "unknown"}

    assert normalize_model_family("gpt-5-mini") == "gpt"
    assert normalize_model_family("claude-sonnet-5") == "claude"
    assert normalize_model_family("gemini-2.5-flash") == "gemini"
    assert normalize_model_family("llama-3.3-70b-versatile") == "llama"
    assert normalize_model_family("deepseek-chat") == "deepseek"
    assert normalize_model_family("qwen3:latest") == "llama"
    assert normalize_model_family("some-arbitrary-model-xyz") == "unknown"
    assert normalize_model_family(None) == "unknown"
    assert normalize_model_family("") == "unknown"

    for model in (
        "gpt-5-mini",
        "claude-sonnet-5",
        "gemini-2.5-flash",
        "llama-3.3-70b-versatile",
        "deepseek-chat",
        "qwen3:latest",
        "unknown-model",
    ):
        assert normalize_model_family(model) in bounded
