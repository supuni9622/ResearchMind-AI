"""
Best-effort LangSmith trace URL lookup (E10's promotion-review queue,
EVALUATION_PLAN.md §3/§15).

The review queue itself never stores or replays a generation's actual
question/answer/context (see `PromotionReview`'s own module docstring
for why -- no surface reliably persists that in our own database).
Instead, a reviewer clicks through to the real trace in LangSmith's own
UI to read it, then fills in the promotion form here by hand. This is
the first *read* this codebase does against LangSmith -- everything
before this (E5/E11/E19/E22) only ever wrote to it.
"""

from __future__ import annotations

from uuid import UUID

import structlog

from app.ai.observability.providers.langsmith.client import get_langsmith_client

logger = structlog.get_logger()


def get_trace_url(run_id: UUID) -> str | None:
    """
    Returns the LangSmith trace URL for `run_id`, or `None` when
    LangSmith isn't configured, the run can't be found, or anything else
    goes wrong -- a lookup failure must degrade to "no link available"
    in the review queue, never a broken page.
    """

    client = get_langsmith_client()
    if client is None:
        return None

    try:
        run = client.read_run(run_id)
        url: str = client.get_run_url(run=run)
        return url
    except Exception:
        logger.warning(
            "observability.langsmith.trace_link_lookup_failed",
            run_id=str(run_id),
            exc_info=True,
        )
        return None
