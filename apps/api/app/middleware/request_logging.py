# Responsibility is:

# Log every HTTP request
# Log every HTTP response

# This file is request pipeline logic.

import structlog
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger()


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        logger.info(
            "Request started",
            method=request.method,
            path=request.url.path,
        )

        response = await call_next(request)

        logger.info(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
        )

        return response
