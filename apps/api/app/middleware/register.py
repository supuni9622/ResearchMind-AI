from fastapi import FastAPI

from app.middleware.cors import get_cors_middleware
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.request_logging import LoggingMiddleware
from app.middleware.request_timing import TimingMiddleware


def register_middlewares(app: FastAPI) -> None:
    """
    Register all application middleware.

    Middleware execution order is important.

    Request Flow
    ------------

    Request
        │
        ▼
    CORS
        │
        ▼
    Request ID
        │
        ▼
    Request Logging
        │
        ▼
    Request Timing
        │
        ▼
    Route Handler
        │
        ▼
    Response
    """

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------

    cors = get_cors_middleware()

    app.add_middleware(
        cors["middleware_class"],
        **{k: v for k, v in cors.items() if k != "middleware_class"},
    )

    # ------------------------------------------------------------------
    # Request ID
    # ------------------------------------------------------------------

    app.add_middleware(RequestIDMiddleware)

    # ------------------------------------------------------------------
    # Request Logging
    # ------------------------------------------------------------------

    app.add_middleware(LoggingMiddleware)

    # ------------------------------------------------------------------
    # Request Timing
    # ------------------------------------------------------------------

    app.add_middleware(TimingMiddleware)