"""create feedback table

Revision ID: 591ddffcd0d7
Revises: d08167d834fb
Create Date: 2026-08-11 01:10:54.996229

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "591ddffcd0d7"
down_revision: str | Sequence[str] | None = "d08167d834fb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "feedback",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("generation_id", sa.UUID(), nullable=False),
        sa.Column("surface", sa.String(length=30), nullable=False),
        sa.Column("rating", sa.String(length=10), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "generation_id", name="uq_feedback_owner_generation"),
    )
    op.create_index("ix_feedback_owner_id", "feedback", ["owner_id"])
    op.create_index("ix_feedback_generation_id", "feedback", ["generation_id"])


def downgrade() -> None:
    op.drop_table("feedback")
