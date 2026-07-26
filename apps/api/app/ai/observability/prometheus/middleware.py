"""
ASGI HTTP metrics middleware (Prometheus Grafana Observability PRD §17).

Deliberately a raw ASGI middleware, not `starlette.middleware.base.
BaseHTTPMiddleware`: it needs to read `scope["route"]` *after* Starlette's
router has resolved it (to get the templated path, e.g.
`/api/v1/research/{research_id}`, never a raw UUID -- PRD §15 "Route
normalization") and to guarantee the in-flight gauge is decremented in a
`finally` no matter how the response completes.

Metric recording is best-effort throughout (PRD §5.4): any failure here
is logged and swallowed, never allowed to break the request it observes.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

import structlog

from app.ai.observability.prometheus.names import HTTP_BUCKETS
from app.ai.observability.prometheus.registry import PrometheusMetricRegistry

logger = structlog.get_logger()

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]

_REQUESTS_TOTAL = "researchmind_http_requests_total"
_REQUEST_DURATION = "researchmind_http_request_duration_seconds"
_IN_FLIGHT = "researchmind_http_in_flight_requests"
_ERRORS_TOTAL = "researchmind_http_errors_total"


def _route_template(scope: Scope) -> str:
    """
    Reconstructs the templated path (e.g. `/api/v1/research/{research_id}`,
    never a raw id -- PRD §15 "Route normalization") from the raw request
    path plus `scope["path_params"]`, rather than trusting
    `scope["route"].path`: with this app's FastAPI version, nested
    `include_router()` prefixes are resolved lazily, and the `APIRoute`
    object left in `scope["route"]` keeps only its *local*, unprefixed
    path (e.g. `/health/live` for a route actually served at
    `/api/v1/health/live`).

    An unmatched route (404s, arbitrary probing) collapses to a fixed
    "unmatched" label instead of the raw path, so it can never become an
    unbounded-cardinality series. Checked via `scope["endpoint"]`, not
    `scope["route"]`: both Starlette's and FastAPI's routers set
    `endpoint` on every match (a plain Starlette `Route` never sets
    `route` at all), so this is the one signal that reliably means "a
    route matched" across both.
    """

    if scope.get("endpoint") is None:
        return "unmatched"

    template = str(scope.get("path", "unknown"))

    for name, value in (scope.get("path_params") or {}).items():
        template = template.replace(str(value), f"{{{name}}}", 1)

    return template


class PrometheusHTTPMiddleware:
    def __init__(
        self,
        app: Callable[[Scope, Receive, Send], Awaitable[None]],
        *,
        metric_registry: PrometheusMetricRegistry,
    ) -> None:
        self.app = app

        self._requests_total = metric_registry.get_counter(
            _REQUESTS_TOTAL,
            "Total HTTP requests.",
            ("method", "route", "status_code"),
        )
        self._request_duration = metric_registry.get_histogram(
            _REQUEST_DURATION,
            "HTTP request duration in seconds.",
            ("method", "route"),
            HTTP_BUCKETS,
        )
        self._in_flight = metric_registry.get_gauge(
            _IN_FLIGHT,
            "In-flight HTTP requests.",
        )
        self._errors_total = metric_registry.get_counter(
            _ERRORS_TOTAL,
            "Total HTTP requests that raised an unhandled exception.",
            ("method", "route"),
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        method = str(scope.get("method", "UNKNOWN"))
        status_code = 500
        started = time.perf_counter()

        try:
            self._in_flight.inc()
        except Exception as exc:
            logger.warning(
                "prometheus.http_middleware.record_failed", error_type=type(exc).__name__
            )

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message.get("type") == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            try:
                self._errors_total.labels(method=method, route=_route_template(scope)).inc()
            except Exception as exc:
                logger.warning(
                    "prometheus.http_middleware.record_failed",
                    error_type=type(exc).__name__,
                )
            raise
        finally:
            route = _route_template(scope)
            try:
                self._requests_total.labels(
                    method=method,
                    route=route,
                    status_code=str(status_code),
                ).inc()
                self._request_duration.labels(method=method, route=route).observe(
                    time.perf_counter() - started
                )
            except Exception as exc:
                logger.warning(
                    "prometheus.http_middleware.record_failed",
                    error_type=type(exc).__name__,
                )
            try:
                self._in_flight.dec()
            except Exception as exc:
                logger.warning(
                    "prometheus.http_middleware.record_failed", error_type=type(exc).__name__
                )
