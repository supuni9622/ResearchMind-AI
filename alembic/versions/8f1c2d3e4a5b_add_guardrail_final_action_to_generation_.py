"""add guardrail final action to generation usage

Revision ID: 8f1c2d3e4a5b
Revises: 37d9f41035ed
Create Date: 2026-08-11 17:05:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "8f1c2d3e4a5b"
down_revision: str | Sequence[str] | None = "37d9f41035ed"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "generation_usage",
        sa.Column("guardrail_final_action", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("generation_usage", "guardrail_final_action")
