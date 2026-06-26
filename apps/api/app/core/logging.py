from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from app.core.settings import settings

_NOISY_LOGGERS = [
    "uvicorn.access",  # replaced by our LoggingMiddleware
    "sqlalchemy.engine",  # too verbose at INFO
    "httpx",
    "httpcore",
]


def configure_logging() -> None:
    """
    Configure structlog as the primary logging system.

    In development:  coloured ConsoleRenderer (human-readable)
    In production:   JSONRenderer (machine-parseable, one line per event)

    Stdlib loggers (uvicorn, SQLAlchemy, etc.) are routed through the same
    structlog processor chain via ProcessorFormatter so every log line shares
    the same format and carries the same contextvars (e.g. request_id).
    """

    is_production = settings.environment == "production"

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    renderer: Any = (
        structlog.processors.ExceptionRenderer()
        if is_production
        else structlog.dev.ConsoleRenderer()
    )

    # Configure structlog's own loggers.
    structlog.configure(
        processors=shared_processors + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )

    # Build the formatter used for both native structlog and bridged stdlib logs.
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
