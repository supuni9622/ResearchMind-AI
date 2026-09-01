"""add project_id to research_proposals and research_runs

Revision ID: dfffb70dfaa8
Revises: c86fbdb57b2b
Create Date: 2026-09-01 00:00:00.000000

Carries a project scope forward through the Deep Research proposal ->
approval -> run -> LangGraph execution chain, for the case where a brand
new conversation (no conversation_id yet) is being started inside a
project -- ResearchConversation.project_id itself is only set once the
conversation row is actually created (see ResearchService.
publish_runtime_report), so these columns exist purely to carry the
value forward until that point.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "dfffb70dfaa8"
down_revision: str | Sequence[str] | None = "c86fbdb57b2b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "research_proposals",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_research_proposals_project_id_projects",
        "research_proposals",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_research_proposals_project_id", "research_proposals", ["project_id"])

    op.add_column(
        "research_runs",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_research_runs_project_id_projects",
        "research_runs",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_research_runs_project_id", "research_runs", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_research_runs_project_id", table_name="research_runs")
    op.drop_constraint("fk_research_runs_project_id_projects", "research_runs", type_="foreignkey")
    op.drop_column("research_runs", "project_id")

    op.drop_index("ix_research_proposals_project_id", table_name="research_proposals")
    op.drop_constraint(
        "fk_research_proposals_project_id_projects", "research_proposals", type_="foreignkey"
    )
    op.drop_column("research_proposals", "project_id")
