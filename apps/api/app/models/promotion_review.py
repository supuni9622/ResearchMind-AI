"""Human-confirmed golden-set/production-failures promotions (E10,
EVALUATION_PLAN.md §3/§15's "both directions" promotion loop).

A row only ever exists for a candidate a human has already reviewed --
unreviewed candidates are derived live from `Feedback`/`eval_scores`
(`PromotionReviewRepository.list_candidates()`), not persisted here.
`status=rejected` rows exist purely so a rejected candidate doesn't keep
reappearing in the queue; `status=confirmed` rows additionally carry the
manually-authored `GoldenExample` fields a reviewer filled in after
reading the real content via the LangSmith trace link (this table
intentionally does not store the original question/answer/context
itself -- see the tracker's E10 entry for why).

`sync_promoted_examples.py` reads `status=confirmed, synced=false` rows
and appends them to `rag_answer_gold.json` (direction=good) or
`production_failures.json` (direction=failure), then marks them synced
-- the same two-step, git-reviewable-diff pattern already established by
`persist_golden_set_scores.py`, deliberately not a direct API-to-file
write.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PromotionReview(Base):
    __tablename__ = "promotion_reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Which candidate this review is for.
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    """One of `PromotionCandidateSource`."""
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    """One of `PromotionDirection`."""
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    generation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    """No FK to `generation_usage.generation_id` -- that column isn't
    unique, matching `Feedback`/`EvalScore`'s already-established
    pattern for this exact field."""

    # Review outcome.
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    """One of `PromotionStatus`."""
    reviewed_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Manually-authored GoldenExample fields -- only set when
    # status=confirmed. Field names/types deliberately mirror
    # `benchmarks.generation.golden_dataset.GoldenExample` so
    # `sync_promoted_examples.py` can construct one directly, no
    # translation layer.
    question: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    contexts: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    reference_context_ids: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    expected_citation_ids: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    query_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String(10), nullable=True)
    workflow: Mapped[str | None] = mapped_column(String(30), nullable=True)
    rubric: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_category: Mapped[str | None] = mapped_column(String(30), nullable=True)
    """One of `FailureCategory` -- set only for `direction=failure`."""

    # Sync state, written by `sync_promoted_examples.py`, never by the API.
    synced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
