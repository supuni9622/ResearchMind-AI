"""Per-metric evaluation scores, owner-scoped (EVALUATION_PLAN.md §14/§16 phase 6/7).

Created by E5 (online risk-weighted scoring) as the minimal persistence
this job needs to satisfy its own acceptance criteria ("every
guardrail-flagged production request has a recorded score"). E6 extends
this same table rather than building a separate one -- attaching
`POST /feedback` submissions and E1/E2's offline benchmark results here
too, per EVALUATION_PLAN.md §6's "so E7's dashboard has one place to
query, not three."
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EvalScore(Base):
    """
    One row per (generation, metric, source) for online/human-feedback
    rows, or (dataset_example_id, metric, source) for offline-benchmark
    rows -- e.g. a single generation scored online produces one row for
    `citation_validity` and, when sampled for judge scoring, one more per
    Ragas metric (`answer_relevancy`, `faithfulness`, ...).

    `owner_id`/`generation_id` are nullable because offline-benchmark
    rows (E6) belong to neither a user nor a live production generation
    -- they score a fixed golden-dataset example instead, identified by
    `dataset_example_id`. The check constraint below is what keeps every
    row traceable to *something*. `generation_id` intentionally has no
    foreign key to `generation_usage.generation_id`, matching
    `Feedback`'s and `GenerationUsage.conversation_id`/`session_id`'s
    established pattern: that column isn't unique (`request_id` is), so
    it can't be an FK target.

    Offline rows are deliberately append-only, not deduplicated by
    `uq_eval_scores_generation_metric_source`: that constraint is keyed
    on `generation_id`, which is `NULL` for every offline row, and
    Postgres treats `NULL` as distinct from every other `NULL` in a
    unique constraint by default -- so re-running the same benchmark
    against the same example/metric correctly produces a new row (a
    trend data point for E9), not a conflict.
    """

    __tablename__ = "eval_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    generation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    metric_name: Mapped[str] = mapped_column(String(50), nullable=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    """One of `EvalScoreSource` (app/models/enums.py)."""
    sample_category: Mapped[str | None] = mapped_column(String(30), nullable=True)
    """
    Why this generation was scored -- one of `SamplingCategory`
    (`app/ai/runtime/generation/online_scoring/sampling.py`). Null for
    non-online sources (offline benchmark rows, human feedback), where
    sampling doesn't apply.
    """
    dataset_example_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    """Set only for `source=offline_benchmark` rows, per EVALUATION_PLAN.md §16 phase 6."""
    comment_classification: Mapped[str | None] = mapped_column(String(20), nullable=True)
    """
    Mirrors `Feedback.comment_classification` (E11) onto the
    `user_rating` row `FeedbackService.submit()` writes here, one of
    `CommentClassification` -- lets E9/E10 filter/aggregate on it
    without joining back to `feedback`, same "one place to query"
    rationale as this table's own docstring. Null for every other
    metric/source, and for `user_rating` rows with no comment to
    classify.
    """
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "generation_id", "metric_name", "source", name="uq_eval_scores_generation_metric_source"
        ),
        CheckConstraint(
            "generation_id IS NOT NULL OR dataset_example_id IS NOT NULL",
            name="ck_eval_scores_has_generation_or_example",
        ),
    )
