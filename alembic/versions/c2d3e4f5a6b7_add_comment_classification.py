"""add comment_classification to feedback and eval_scores

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-08-12 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c2d3e4f5a6b7"
down_revision: str | Sequence[str] | None = "b1c2d3e4f5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "feedback",
        sa.Column("comment_classification", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "eval_scores",
        sa.Column("comment_classification", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("eval_scores", "comment_classification")
    op.drop_column("feedback", "comment_classification")
