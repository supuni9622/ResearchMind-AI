from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger()


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Starlette adds middleware in reverse — this runs before RequestIDMiddleware.
        # Generate request_id here so it is available in contextvars for the full
        # request lifecycle. RequestIDMiddleware reads it back for the response header.
        request_id = getattr(request.state, "request_id", None)
        if not request_id:
            request_id = str(uuid.uuid4())
            request.state.request_id = request_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client=request.client.host if request.client else None,
        )

        logger.info(
            "http.request",
            query=str(request.url.query) or None,
            user_agent=request.headers.get("user-agent"),
        )

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
