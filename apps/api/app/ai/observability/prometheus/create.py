"""
Prometheus platform composition root (Prometheus Grafana Observability
PRD §12/§38 Milestone 1). Every other platform's `create.py` calls
`get_metrics_recorder()` to obtain the `MetricsRecorder` it wires into
its service -- this module is the only place that knows whether
Prometheus is enabled or what backs the recorder.
"""

from __future__ import annotations

from functools import lru_cache

import structlog
from prometheus_client import PlatformCollector, ProcessCollector, start_http_server
from starlette.types import ASGIApp

from app.ai.observability.prometheus.endpoint import build_metrics_asgi_app
from app.ai.observability.prometheus.recorder import PrometheusMetricsRecorder
from app.ai.observability.prometheus.registry import PrometheusMetricRegistry
from app.core.settings import settings
from app.infrastructure.metrics.interfaces import MetricsRecorder
from app.infrastructure.metrics.noop import NoOpMetricsRecorder

logger = structlog.get_logger()


@lru_cache
def get_prometheus_metric_registry() -> PrometheusMetricRegistry:
    metric_registry = PrometheusMetricRegistry()

    if settings.prometheus_include_process_metrics:
        ProcessCollector(registry=metric_registry.registry)

    if settings.prometheus_include_platform_metrics:
        PlatformCollector(registry=metric_registry.registry)

    return metric_registry


@lru_cache
def get_metrics_recorder() -> MetricsRecorder:
    """
    Returns the application-wide `MetricsRecorder`. `NoOpMetricsRecorder`
    when Prometheus is disabled (`PROMETHEUS_ENABLED=false`) -- every
    business service already tolerates that recorder, so disabling
    Prometheus never changes application behavior (PRD §5.4/§42
    "PROMETHEUS_ENABLED as a rollback flag").
    """

    if not settings.prometheus_enabled:
        return NoOpMetricsRecorder()

    return PrometheusMetricsRecorder(get_prometheus_metric_registry())


def get_metrics_asgi_app() -> ASGIApp | None:
    """`None` when Prometheus is disabled -- the composition root then
    skips mounting `/metrics` entirely (PRD §11 "absent or disabled when
    configured off")."""

    if not settings.prometheus_enabled:
        return None

    return build_metrics_asgi_app(get_prometheus_metric_registry())


def start_worker_metrics_server(port: int) -> None:
    """E17 follow-up (2026-08-12): exposes *this process's* Prometheus
    registry over HTTP on `port`, for a worker process that has no ASGI
    app to mount `/metrics` on (unlike the API, `get_metrics_asgi_app()`
    above). Each OS process gets its own `PrometheusMetricRegistry`
    (`get_prometheus_metric_registry()` is `@lru_cache`d *per process*,
    not shared across the API and its workers) -- confirmed live that a
    metric recorded inside a worker never reached the API's own
    `/metrics/`, the only scrape target that existed before this, since
    the two processes' registries are entirely separate in-memory
    objects. `start_http_server()` runs a WSGI server on a background
    daemon thread (`prometheus_client`'s own standard mechanism for
    exposing metrics from a non-web-framework process) -- non-blocking,
    safe to call once at worker startup before entering the main
    asyncio loop. No-ops when Prometheus is disabled, matching
    `get_metrics_asgi_app()`'s own gate.
    """

    if not settings.prometheus_enabled:
        return

    start_http_server(port, registry=get_prometheus_metric_registry().registry)
