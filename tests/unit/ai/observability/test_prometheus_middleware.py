"""
Unit tests for `PrometheusHTTPMiddleware` (prometheus_grafana_
observability_prd.md §17).

Covers:
- a successful request increments the requests-total counter with the
  templated route (via `scope["route"]`), not a raw path
- the in-flight gauge returns to zero after the request completes
- an unhandled exception still increments the error counter and the
  requests-total counter (with the default 500 status), and re-raises
"""

from __future__ import annotations

import pytest
from app.ai.observability.prometheus.middleware import PrometheusHTTPMiddleware
from app.ai.observability.prometheus.registry import PrometheusMetricRegistry
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route


def _build_app(metric_registry: PrometheusMetricRegistry) -> Starlette:
    async def ok(request):
        return PlainTextResponse("ok")

    async def boom(request):
        raise RuntimeError("boom")

    app = Starlette(routes=[Route("/ok", ok), Route("/boom", boom)])
    app.add_middleware(PrometheusHTTPMiddleware, metric_registry=metric_registry)
    return app


async def test_successful_request_increments_counters_with_templated_route() -> None:
    registry = PrometheusMetricRegistry()
    app = _build_app(registry)

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    sent = []

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/ok",
        "headers": [],
        "query_string": b"",
    }

    await app(scope, receive, send)

    value = registry.registry.get_sample_value(
        "researchmind_http_requests_total",
        {"method": "GET", "route": "/ok", "status_code": "200"},
    )
    assert value == 1.0

    in_flight = registry.registry.get_sample_value("researchmind_http_in_flight_requests")
    assert in_flight == 0.0


async def test_unhandled_exception_increments_error_counter_and_reraises() -> None:
    registry = PrometheusMetricRegistry()
    app = _build_app(registry)

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        return None

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/boom",
        "headers": [],
        "query_string": b"",
    }

    with pytest.raises(RuntimeError):
        await app(scope, receive, send)

    errors = registry.registry.get_sample_value(
        "researchmind_http_errors_total",
        {"method": "GET", "route": "/boom"},
    )
    assert errors == 1.0

    requests_total = registry.registry.get_sample_value(
        "researchmind_http_requests_total",
        {"method": "GET", "route": "/boom", "status_code": "500"},
    )
    assert requests_total == 1.0

    in_flight = registry.registry.get_sample_value("researchmind_http_in_flight_requests")
    assert in_flight == 0.0
