"""create eval scores table

Revision ID: 9a2b3c4d5e6f
Revises: 8f1c2d3e4a5b
Create Date: 2026-08-11 17:06:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "9a2b3c4d5e6f"
down_revision: str | Sequence[str] | None = "8f1c2d3e4a5b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "eval_scores",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("generation_id", sa.UUID(), nullable=False),
        sa.Column("metric_name", sa.String(length=50), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("sample_category", sa.String(length=30), nullable=True),
        sa.Column("dataset_example_id", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "generation_id", "metric_name", "source", name="uq_eval_scores_generation_metric_source"
        ),
    )
    op.create_index("ix_eval_scores_owner_id", "eval_scores", ["owner_id"])
    op.create_index("ix_eval_scores_generation_id", "eval_scores", ["generation_id"])


def downgrade() -> None:
    op.drop_table("eval_scores")
