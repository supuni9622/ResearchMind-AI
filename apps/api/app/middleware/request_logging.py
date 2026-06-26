from __future__ import annotations

import time

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger()


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Bind per-request fields to structlog contextvars so every log line
        # emitted during this request automatically carries them.
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=getattr(request.state, "request_id", None),
            method=request.method,
            path=request.url.path,
            client=request.client.host if request.client else None,
        )

        logger.info("http.request")

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        logger.info(
            "http.response",
            status=response.status_code,
            duration_ms=duration_ms,
        )

        structlog.contextvars.clear_contextvars()

        return response  # type: ignore[no-any-return]
