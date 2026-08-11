"""add langsmith run id to generation usage

Revision ID: 37d9f41035ed
Revises: 6780da85eec7
Create Date: 2026-08-11 15:47:21.781328

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "37d9f41035ed"
down_revision: str | Sequence[str] | None = "6780da85eec7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "generation_usage",
        sa.Column("langsmith_run_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        op.f("ix_generation_usage_langsmith_run_id"),
        "generation_usage",
        ["langsmith_run_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_generation_usage_langsmith_run_id"), table_name="generation_usage")
    op.drop_column("generation_usage", "langsmith_run_id")
