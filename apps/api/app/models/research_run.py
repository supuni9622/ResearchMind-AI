"""Owner-scoped lifecycle records for resumable Research Runtime executions."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin


class ResearchRun(TimestampMixin, Base):
    """Execution lifecycle, distinct from a completed public ResearchSession."""

    __tablename__ = "research_runs"
    __table_args__ = (
        UniqueConstraint("owner_id", "idempotency_key", name="uq_research_runs_owner_idempotency"),
        Index("ix_research_runs_owner_status", "owner_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    research_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_sessions.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    parent_research_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research_sessions.id", ondelete="SET NULL"), nullable=True
    )
    graph_thread_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    current_phase: Mapped[str | None] = mapped_column(String(100), nullable=True)
    terminal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    request_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cancellation_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    budget_profile: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    budget_usage: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    error_summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
