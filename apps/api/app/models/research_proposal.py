"""Owner-scoped, approval-gated Deep Research proposals."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin


class ResearchProposal(TimestampMixin, Base):
    """Compact plan/request record created before a user authorizes a run."""

    __tablename__ = "research_proposals"
    __table_args__ = (Index("ix_research_proposals_owner_status", "owner_id", "status"),)

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
    # Only meaningful when conversation_id is still None at proposal time
    # (a brand-new conversation, not yet created -- see
    # ResearchService.publish_runtime_report, which is where the
    # conversation row, and hence its own project_id, is actually
    # created). Carried here so approval/execution can thread it through
    # without re-deriving it. Once a conversation exists, its own stored
    # project_id is authoritative, not this field.
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    request: Mapped[dict] = mapped_column(JSONB, nullable=False)
    plan: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    research_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_runs.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
