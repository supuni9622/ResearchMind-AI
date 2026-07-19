"""add conversation title generation lease

Revision ID: f0e1d2c3b4a5
Revises: cfd2f848f25b
Create Date: 2026-07-19 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f0e1d2c3b4a5"
down_revision: str | Sequence[str] | None = "cfd2f848f25b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add an expiring claim used to make auto-title generation one-time."""

    op.add_column("conversations", sa.Column("title_generation_token", sa.UUID(), nullable=True))
    op.add_column(
        "conversations",
        sa.Column("title_generation_started_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Remove title-generation lease columns."""

    op.drop_column("conversations", "title_generation_started_at")
    op.drop_column("conversations", "title_generation_token")
