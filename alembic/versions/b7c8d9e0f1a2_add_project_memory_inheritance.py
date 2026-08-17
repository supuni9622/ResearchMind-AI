"""Add the project personal-memory inheritance control.

Revision ID: b7c8d9e0f1a2
Revises: a6b7c8d9e0f1
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b7c8d9e0f1a2"
down_revision: str | None = "a6b7c8d9e0f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "memory_scope_settings",
        sa.Column(
            "inherit_personal_memory", sa.Boolean(), server_default=sa.true(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_column("memory_scope_settings", "inherit_personal_memory")
