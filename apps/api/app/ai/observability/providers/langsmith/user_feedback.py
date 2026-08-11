"""
Best-effort bridge from ResearchMind's own `feedback` table into LangSmith's
`create_feedback()` API (EVALUATION_IMPLEMENTATION_TRACKER.md E21's
LangSmith-feedback follow-up) -- gives a user's thumbs up/down visibility in
LangSmith's own trace UI, correlated to the exact run, on top of (not
instead of) our own `feedback` table, which stays the source of truth for
the product surface.
"""

from __future__ import annotations

from uuid import UUID

import structlog

from app.ai.observability.providers.langsmith.client import get_langsmith_client
from app.models.enums import FeedbackRating

logger = structlog.get_logger()

_RATING_SCORE: dict[FeedbackRating, float] = {
    FeedbackRating.UP: 1.0,
    FeedbackRating.DOWN: 0.0,
}


def sync_user_feedback(
    *,
    run_id: UUID,
    feedback_id: UUID,
    rating: FeedbackRating,
    comment: str | None,
) -> None:
    """
    Mirrors one `Feedback` row into LangSmith under the `user_rating` key.

    `feedback_id` is our own `Feedback.id`, reused verbatim as LangSmith's
    `feedback_id`: confirmed empirically (matching the E19 golden-dataset
    sync lesson -- verify against the real account, don't trust the SDK's
    naming) that `create_feedback()` upserts in place on a repeated
    `feedback_id` rather than creating a duplicate, so a user changing
    their vote (our own upsert-on-resubmit semantics, see
    `FeedbackRepository.upsert`) updates the same LangSmith record.

    No-op, not an error, when LangSmith isn't configured or the call
    fails -- a LangSmith hiccup must never break the primary feedback
    write it decorates.
    """

    client = get_langsmith_client()
    if client is None:
        return

    try:
        client.create_feedback(
            run_id=run_id,
            key="user_rating",
            score=_RATING_SCORE[rating],
            comment=comment,
            feedback_id=feedback_id,
        )
    except Exception:
        logger.warning(
            "observability.langsmith.user_feedback_failed",
            feedback_id=str(feedback_id),
            exc_info=True,
        )
