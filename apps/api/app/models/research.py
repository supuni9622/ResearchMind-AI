from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin


class ResearchSession(TimestampMixin, Base):
    """
    A completed research question/answer, owned by a ResearchMind user
    (research_api_prd.md §14).

    Postgres is the live read path for `GET /research/{id}` -- `answer`,
    `citations`, and `sources` are stored here directly rather than
    reconstructed from the (best-effort, write-only) Research Artifact,
    matching this codebase's existing Conversation/Chat precedent.
    """

    __tablename__ = "research_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    query: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    answer: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    citations: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    sources: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    runtime_metadata: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
