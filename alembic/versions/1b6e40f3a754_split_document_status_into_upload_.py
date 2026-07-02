"""split document status into upload_status and processing_status

Revision ID: 1b6e40f3a754
Revises: a97b3b8eee9f
Create Date: 2026-07-02 09:50:21.940318

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1b6e40f3a754"
down_revision: str | Sequence[str] | None = "a97b3b8eee9f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


upload_status_enum = postgresql.ENUM(
    "PENDING",
    "UPLOADING",
    "COMPLETED",
    "FAILED",
    name="document_upload_status",
)
processing_status_enum = postgresql.ENUM(
    "PENDING",
    "PROCESSING",
    "COMPLETED",
    "FAILED",
    name="document_processing_status",
)
document_status_enum = postgresql.ENUM(
    "UPLOADED",
    "PROCESSING",
    "READY",
    "FAILED",
    "DELETED",
    name="document_status",
)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    upload_status_enum.create(bind, checkfirst=True)
    processing_status_enum.create(bind, checkfirst=True)

    op.add_column("documents", sa.Column("upload_status", upload_status_enum, nullable=False))
    op.add_column(
        "documents", sa.Column("processing_status", processing_status_enum, nullable=False)
    )
    op.add_column("documents", sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("documents", sa.Column("processing_error", sa.Text(), nullable=True))
    op.drop_column("documents", "status")

    document_status_enum.drop(bind, checkfirst=True)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()

    document_status_enum.create(bind, checkfirst=True)

    op.add_column(
        "documents", sa.Column("status", document_status_enum, autoincrement=False, nullable=False)
    )
    op.drop_column("documents", "processing_error")
    op.drop_column("documents", "processed_at")
    op.drop_column("documents", "processing_status")
    op.drop_column("documents", "upload_status")

    upload_status_enum.drop(bind, checkfirst=True)
    processing_status_enum.drop(bind, checkfirst=True)
