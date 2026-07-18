"""
LangSmith provider composition root.
"""

from __future__ import annotations

from functools import lru_cache

from app.ai.observability.providers.langsmith.recorder import LangSmithMetricsRecorder
from app.ai.observability.providers.langsmith.tracing import NoOpTracer, RuntimeTracer
from app.core.settings import settings
from app.infrastructure.metrics.interfaces import MetricsRecorder
from app.infrastructure.metrics.noop import NoOpMetricsRecorder


def _langsmith_enabled() -> bool:
    """
    Tracing needs both an API key *and* the explicit `LANGSMITH_TRACING`
    opt-in -- lets ops keep the key configured in the environment while
    switching tracing off (e.g. locally) without unsetting it.
    """

    return bool(settings.langsmith_api_key and settings.langsmith_tracing)


@lru_cache
def create_runtime_tracer() -> RuntimeTracer:
    """
    Returns a `LangSmithTracer` when LangSmith is enabled (see
    `_langsmith_enabled`), else `NoOpTracer` -- callers always get a
    usable `RuntimeTracer`, never `None`, so `GenerationService` (and any
    future caller) doesn't need its own "is tracing configured" branch.
    """

    if not _langsmith_enabled():
        return NoOpTracer()

    from app.ai.observability.providers.langsmith.tracing import LangSmithTracer

    return LangSmithTracer(project_name=settings.langsmith_project)


@lru_cache
def create_langsmith_metrics_recorder() -> MetricsRecorder:
    """
    Returns a `LangSmithMetricsRecorder` when LangSmith is enabled, else
    `NoOpMetricsRecorder` -- same always-usable-instance shape as
    `create_runtime_tracer()`.
    """

    if not _langsmith_enabled():
        return NoOpMetricsRecorder()

    return LangSmithMetricsRecorder()
