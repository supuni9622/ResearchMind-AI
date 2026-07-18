"""
LangSmith client factory (AI Runtime Observability PRD §11).

LangSmith owns tracing/experiments/datasets/comparisons -- ResearchMind
should not rebuild that infrastructure, only feed it trace
metadata/tags/metrics (PRD §11.1). This module is the one place a
`langsmith.Client` gets constructed, gated on `settings.langsmith_api_key`
being set. Every caller treats a `None` return as "LangSmith is not
configured" and degrades to a no-op -- never raises for a missing key.
"""

from __future__ import annotations

from functools import lru_cache

import structlog

from app.core.settings import settings

logger = structlog.get_logger()


@lru_cache
def get_langsmith_client():  # noqa: ANN201 -- return type is langsmith.Client | None, imported lazily below
    """
    Lazily imports and constructs a `langsmith.Client`. Returns `None`
    (not raising) when `langsmith_api_key` isn't configured, or when the
    `langsmith` package/client construction fails for any reason --
    tracing is always best-effort (PRD §13).
    """

    if not settings.langsmith_api_key:
        return None

    try:
        from langsmith import Client

        return Client(
            api_key=settings.langsmith_api_key,
            api_url=settings.langsmith_endpoint,
        )
    except Exception:
        logger.warning("observability.langsmith.client_unavailable", exc_info=True)
        return None
