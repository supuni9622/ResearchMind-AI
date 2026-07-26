"""
`GET /metrics` (Prometheus Grafana Observability PRD §11). Built against
this application's own `PrometheusMetricRegistry`, never the
`prometheus_client` default global registry -- keeps the exposed series
limited to what this app explicitly registered and lets tests build an
isolated registry/app pair without cross-test leakage.
"""

from __future__ import annotations

from prometheus_client import make_asgi_app
from starlette.types import ASGIApp

from app.ai.observability.prometheus.registry import PrometheusMetricRegistry


def build_metrics_asgi_app(metric_registry: PrometheusMetricRegistry) -> ASGIApp:
    return make_asgi_app(registry=metric_registry.registry)
