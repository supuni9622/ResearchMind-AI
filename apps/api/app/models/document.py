from __future__ import annotations

import uuid

from sqlalchemy import BigInteger, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.models.enums import DocumentStatus


class Document(TimestampMixin, Base):
    """
    Uploaded document owned by a ResearchMind user.

    Stores document metadata only.

    The document contents live in Amazon S3.
    """

    __tablename__ = "documents"

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

    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    storage_key: Mapped[str] = mapped_column(
        String(1024),
        unique=True,
        nullable=False,
    )

    content_type: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    checksum: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    status: Mapped[DocumentStatus] = mapped_column(
        Enum(
            DocumentStatus,
            name="document_status",
        ),
        default=DocumentStatus.UPLOADED,
        nullable=False,
    )
