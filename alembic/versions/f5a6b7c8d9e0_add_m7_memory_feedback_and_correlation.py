"""Add M7 memory feedback and generation correlation.

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "f5a6b7c8d9e0"
down_revision: str | None = "e4f5a6b7c8d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "generation_usage",
        sa.Column(
            "injected_memory_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            server_default="{}",
            nullable=False,
        ),
    )
    op.create_table(
        "memory_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("generation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("surface", sa.String(length=30), nullable=False),
        sa.Column("signal", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "owner_id", "generation_id", name="uq_memory_feedback_owner_generation"
        ),
    )
    op.create_index("ix_memory_feedback_owner_id", "memory_feedback", ["owner_id"])
    op.create_index("ix_memory_feedback_generation_id", "memory_feedback", ["generation_id"])


def downgrade() -> None:
    op.drop_index("ix_memory_feedback_generation_id", table_name="memory_feedback")
    op.drop_index("ix_memory_feedback_owner_id", table_name="memory_feedback")
    op.drop_table("memory_feedback")
    op.drop_column("generation_usage", "injected_memory_ids")
