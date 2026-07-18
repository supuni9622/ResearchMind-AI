"""
Unit tests for the LangSmith provider composition root.

Covers:
- create_runtime_tracer()/create_langsmith_metrics_recorder() return the
  NoOp variant unless BOTH langsmith_api_key and langsmith_tracing are
  set -- an API key alone (tracing left off) must not enable tracing
"""

from __future__ import annotations

from app.ai.observability.providers.langsmith.create import (
    create_langsmith_metrics_recorder,
    create_runtime_tracer,
)
from app.ai.observability.providers.langsmith.recorder import LangSmithMetricsRecorder
from app.ai.observability.providers.langsmith.tracing import LangSmithTracer, NoOpTracer
from app.core.settings import settings
from app.infrastructure.metrics.noop import NoOpMetricsRecorder


def _clear_caches() -> None:
    create_runtime_tracer.cache_clear()
    create_langsmith_metrics_recorder.cache_clear()


async def test_defaults_to_noop_when_unconfigured(monkeypatch) -> None:
    monkeypatch.setattr(settings, "langsmith_api_key", None)
    monkeypatch.setattr(settings, "langsmith_tracing", False)
    _clear_caches()

    assert isinstance(create_runtime_tracer(), NoOpTracer)
    assert isinstance(create_langsmith_metrics_recorder(), NoOpMetricsRecorder)

    _clear_caches()


async def test_stays_noop_when_api_key_set_but_tracing_disabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "langsmith_api_key", "test-key")
    monkeypatch.setattr(settings, "langsmith_tracing", False)
    _clear_caches()

    assert isinstance(create_runtime_tracer(), NoOpTracer)
    assert isinstance(create_langsmith_metrics_recorder(), NoOpMetricsRecorder)

    _clear_caches()


async def test_stays_noop_when_tracing_enabled_but_no_api_key(monkeypatch) -> None:
    monkeypatch.setattr(settings, "langsmith_api_key", None)
    monkeypatch.setattr(settings, "langsmith_tracing", True)
    _clear_caches()

    assert isinstance(create_runtime_tracer(), NoOpTracer)
    assert isinstance(create_langsmith_metrics_recorder(), NoOpMetricsRecorder)

    _clear_caches()


async def test_enables_langsmith_when_both_api_key_and_tracing_are_set(monkeypatch) -> None:
    monkeypatch.setattr(settings, "langsmith_api_key", "test-key")
    monkeypatch.setattr(settings, "langsmith_tracing", True)
    monkeypatch.setattr(settings, "langsmith_project", "MyProject")
    _clear_caches()

    tracer = create_runtime_tracer()
    recorder = create_langsmith_metrics_recorder()

    assert isinstance(tracer, LangSmithTracer)
    assert isinstance(recorder, LangSmithMetricsRecorder)

    _clear_caches()
