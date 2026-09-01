"""add project_id to conversations

Revision ID: d0e1f2a3b4c5
Revises: c8d9e0f1a2b3
Create Date: 2026-09-01 00:00:00.000000

Nullable, ON DELETE SET NULL -- deliberately different from
`memories.project_id` (ON DELETE CASCADE, see e4f5a6b7c8d9): deleting a
project should detach its conversations back to personal scope rather than
destroy chat history. Project-scoped memory still cascades on project
deletion, which is pre-existing, unchanged behavior.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "d0e1f2a3b4c5"
down_revision: str | Sequence[str] | None = "c8d9e0f1a2b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_conversations_project_id_projects",
        "conversations",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_conversations_project_id", "conversations", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_conversations_project_id", table_name="conversations")
    op.drop_constraint("fk_conversations_project_id_projects", "conversations", type_="foreignkey")
    op.drop_column("conversations", "project_id")
