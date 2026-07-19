"""add conversation history compaction state

Revision ID: d9e2f4a6b8c0
Revises: f0e1d2c3b4a5
Create Date: 2026-07-19 19:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d9e2f4a6b8c0"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Store only the bounded prompt summary and its canonical boundary."""

    op.add_column("conversations", sa.Column("history_summary", sa.Text(), nullable=True))
    op.add_column(
        "conversations",
        sa.Column("history_compacted_through_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Remove compaction state; canonical messages are never deleted."""

    op.drop_column("conversations", "history_compacted_through_at")
    op.drop_column("conversations", "history_summary")
