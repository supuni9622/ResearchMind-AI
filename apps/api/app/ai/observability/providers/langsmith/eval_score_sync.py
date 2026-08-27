"""
Best-effort bridge from E5's online scoring job into LangSmith's
`create_feedback()` API -- extends E22's `sync_user_feedback` pattern
(which mirrors *human* feedback) to *automated* signals (citation
validity, Ragas judge scores), so a trace's Feedback column in
LangSmith's own UI shows both halves side by side, not just the human
one.
"""

from __future__ import annotations

from uuid import UUID

import structlog

from app.ai.observability.providers.langsmith.client import get_langsmith_client

logger = structlog.get_logger()


def sync_eval_score(
    *,
    run_id: UUID,
    eval_score_id: UUID,
    metric_name: str,
    score: float | None,
    reason: str | None,
) -> None:
    """
    Mirrors one `eval_scores` row into LangSmith under its own
    `metric_name` key (e.g. `"citation_validity"`, `"faithfulness"`) --
    distinct from `sync_user_feedback`'s single `"user_rating"` key, so
    every automated metric appears as its own feedback entry on the run
    rather than colliding with each other or with human feedback.

    `eval_score_id` (our own `EvalScore.id`) is reused verbatim as
    LangSmith's `feedback_id`, matching `sync_user_feedback`'s already-
    confirmed-empirically upsert-in-place behavior on a repeated
    `feedback_id`.

    No-op, not an error, when LangSmith isn't configured or the call
    fails -- a LangSmith hiccup must never break the online scoring job
    that calls this once per metric per generation.
    """

    client = get_langsmith_client()
    if client is None:
        return

    try:
        client.create_feedback(
            run_id=run_id,
            key=metric_name,
            score=score,
            comment=reason,
            feedback_id=eval_score_id,
        )
    except Exception:
        logger.warning(
            "observability.langsmith.eval_score_sync_failed",
            eval_score_id=str(eval_score_id),
            metric_name=metric_name,
            exc_info=True,
        )
