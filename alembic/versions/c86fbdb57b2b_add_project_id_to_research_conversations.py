"""add project_id to research_conversations

Revision ID: c86fbdb57b2b
Revises: f2a3b4c5d6e7
Create Date: 2026-09-01 00:00:00.000000

Nullable, ON DELETE SET NULL -- same rationale as
d0e1f2a3b4c5_add_project_id_to_conversations. Covers both Linear Research
(ResearchSession.conversation_id) and Deep Research
(ResearchRun.conversation_id), since both hang off research_conversations.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "c86fbdb57b2b"
down_revision: str | Sequence[str] | None = "f2a3b4c5d6e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "research_conversations",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_research_conversations_project_id_projects",
        "research_conversations",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_research_conversations_project_id", "research_conversations", ["project_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_research_conversations_project_id", table_name="research_conversations")
    op.drop_constraint(
        "fk_research_conversations_project_id_projects",
        "research_conversations",
        type_="foreignkey",
    )
    op.drop_column("research_conversations", "project_id")
