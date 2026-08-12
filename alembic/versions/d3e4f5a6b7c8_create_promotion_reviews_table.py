"""create promotion_reviews table

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-08-12 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "d3e4f5a6b7c8"
down_revision: str | Sequence[str] | None = "c2d3e4f5a6b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "promotion_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("direction", sa.String(length=10), nullable=False),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("generation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column(
            "reviewed_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "reviewed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("question", sa.Text(), nullable=True),
        sa.Column("reference_answer", sa.Text(), nullable=True),
        sa.Column("contexts", postgresql.JSONB(), nullable=True),
        sa.Column("reference_context_ids", postgresql.JSONB(), nullable=True),
        sa.Column("expected_citation_ids", postgresql.JSONB(), nullable=True),
        sa.Column("query_type", sa.String(length=30), nullable=True),
        sa.Column("difficulty", sa.String(length=10), nullable=True),
        sa.Column("workflow", sa.String(length=30), nullable=True),
        sa.Column("rubric", sa.Text(), nullable=True),
        sa.Column("failure_category", sa.String(length=30), nullable=True),
        sa.Column("synced", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f("ix_promotion_reviews_owner_id"), "promotion_reviews", ["owner_id"])
    op.create_index(
        op.f("ix_promotion_reviews_generation_id"), "promotion_reviews", ["generation_id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_promotion_reviews_generation_id"), table_name="promotion_reviews")
    op.drop_index(op.f("ix_promotion_reviews_owner_id"), table_name="promotion_reviews")
    op.drop_table("promotion_reviews")
