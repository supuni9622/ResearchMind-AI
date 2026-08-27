"""make eval_scores owner_id/generation_id nullable for offline rows

Revision ID: b1c2d3e4f5a6
Revises: 9a2b3c4d5e6f
Create Date: 2026-08-11 19:10:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "b1c2d3e4f5a6"
down_revision: str | Sequence[str] | None = "9a2b3c4d5e6f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("eval_scores", "owner_id", nullable=True)
    op.alter_column("eval_scores", "generation_id", nullable=True)
    op.create_index(
        op.f("ix_eval_scores_dataset_example_id"),
        "eval_scores",
        ["dataset_example_id"],
    )
    op.create_check_constraint(
        "ck_eval_scores_has_generation_or_example",
        "eval_scores",
        "generation_id IS NOT NULL OR dataset_example_id IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_eval_scores_has_generation_or_example",
        "eval_scores",
        type_="check",
    )
    op.drop_index(
        op.f("ix_eval_scores_dataset_example_id"),
        table_name="eval_scores",
    )
    op.alter_column("eval_scores", "generation_id", nullable=False)
    op.alter_column("eval_scores", "owner_id", nullable=False)
