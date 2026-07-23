"""create research runs table

Revision ID: e2f3a4b5c6d7
Revises: d9e2f4a6b8c0
Create Date: 2026-07-19 22:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "e2f3a4b5c6d7"
down_revision: str | Sequence[str] | None = "d9e2f4a6b8c0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "research_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("research_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("parent_research_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("graph_thread_id", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("current_phase", sa.String(length=100), nullable=True),
        sa.Column("terminal_reason", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "cancellation_requested", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "budget_profile",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "budget_usage",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "error_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["research_conversations.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["parent_research_id"], ["research_sessions.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["research_session_id"], ["research_sessions.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("graph_thread_id"),
        sa.UniqueConstraint(
            "owner_id", "idempotency_key", name="uq_research_runs_owner_idempotency"
        ),
        sa.UniqueConstraint("research_session_id"),
    )
    op.create_index(op.f("ix_research_runs_owner_id"), "research_runs", ["owner_id"], unique=False)
    op.create_index(op.f("ix_research_runs_status"), "research_runs", ["status"], unique=False)
    op.create_index(
        "ix_research_runs_owner_status", "research_runs", ["owner_id", "status"], unique=False
    )
    op.create_index(
        op.f("ix_research_runs_conversation_id"), "research_runs", ["conversation_id"], unique=False
    )


def downgrade() -> None:
    op.drop_table("research_runs")
