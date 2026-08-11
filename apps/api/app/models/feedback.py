"""Owner-scoped thumbs up/down feedback on a single generation."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Feedback(Base):
    """
    One feedback record per (owner, generation) pair.

    Upserted, not append-only, unlike `GenerationUsage` -- a user
    changing their mind (thumbs down -> thumbs up after a re-read)
    should update the same record, not accumulate a history nothing
    downstream needs yet. `generation_id` intentionally has no foreign
    key to `generation_usage.generation_id`: that column isn't unique
    (`request_id` is), so it can't be an FK target -- matches the
    already-established pattern of `GenerationUsage.conversation_id`/
    `session_id` being plain indexed columns rather than enforced FKs.
    """

    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    generation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    surface: Mapped[str] = mapped_column(String(30), nullable=False)
    rating: Mapped[str] = mapped_column(String(10), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    #
    # Objective/preference split (E11, EVALUATION_PLAN.md §12/1g) --
    # one of `CommentClassification`, null whenever there's no comment
    # to classify (rating-only feedback) or classification hasn't run
    # yet. Set once, alongside the comment itself, by
    # `CommentClassificationService` -- never re-classified on a later
    # rating change to the same row.
    #
    comment_classification: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("owner_id", "generation_id", name="uq_feedback_owner_generation"),
    )
