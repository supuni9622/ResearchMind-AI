from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin


class Memory(TimestampMixin, Base):
    """
    Canonical Postgres row backing `MemoryRecord` (memory_platform_prd.md
    §10) for the USER, RESEARCH, and SEMANTIC memory types.

    SESSION memory never reaches this table -- it lives entirely in
    Valkey (PRD §6.1, TTL-bound) via `SessionMemoryService`. SEMANTIC
    (and RESEARCH) rows additionally get an embedding upserted into
    Qdrant by `SemanticMemoryService`/`ResearchMemoryService`, keyed by
    this row's `id`; this table stays the single source of truth for
    CRUD and ownership so `GET/PUT/DELETE /memory/{id}` don't need to
    know which vector index (if any) a record was indexed into.

    The Python attribute is `memory_metadata`, not `metadata` --
    `metadata` is reserved on every SQLAlchemy `DeclarativeBase`
    subclass (mirrors `ResearchSession.runtime_metadata`).
    """

    __tablename__ = "memories"

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

    type: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        index=True,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    memory_metadata: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    importance_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
