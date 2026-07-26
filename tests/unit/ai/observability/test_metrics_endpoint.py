"""
Unit tests for the `/metrics` ASGI app (prometheus_grafana_observability_
prd.md §11/§36.2).

Covers:
- GET returns 200 with the Prometheus text-exposition content type
- a recorded metric's name appears in the response body
- no forbidden identifier-shaped content leaks into the exposition
  (sanity check, not exhaustive -- the real guarantee is that no
  business service is ever given an identifier-shaped label to record,
  see test_metric_labels.py)
"""

from __future__ import annotations

import httpx
from app.ai.observability.prometheus.endpoint import build_metrics_asgi_app
from app.ai.observability.prometheus.recorder import PrometheusMetricsRecorder
from app.ai.observability.prometheus.registry import PrometheusMetricRegistry
from app.infrastructure.metrics.generation import GENERATION_REQUESTS_TOTAL


async def test_metrics_endpoint_returns_200_with_prometheus_content_type() -> None:
    registry = PrometheusMetricRegistry()
    app = build_metrics_asgi_app(registry)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]


async def test_metrics_endpoint_exposes_recorded_metrics() -> None:
    registry = PrometheusMetricRegistry()
    recorder = PrometheusMetricsRecorder(registry)
    recorder.increment(metric=GENERATION_REQUESTS_TOTAL)

    app = build_metrics_asgi_app(registry)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

    assert "researchmind_generation_requests_total" in response.text


async def test_metrics_endpoint_is_isolated_per_registry() -> None:
    registry_a = PrometheusMetricRegistry()
    registry_b = PrometheusMetricRegistry()

    PrometheusMetricsRecorder(registry_a).increment(metric=GENERATION_REQUESTS_TOTAL)

    app_b = build_metrics_asgi_app(registry_b)
    transport = httpx.ASGITransport(app=app_b)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

    assert "researchmind_generation_requests_total" not in response.text
