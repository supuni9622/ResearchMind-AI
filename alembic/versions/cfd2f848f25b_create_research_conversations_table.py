"""create research_conversations table

Revision ID: cfd2f848f25b
Revises: 9ab1f891554a
Create Date: 2026-07-19 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cfd2f848f25b"
down_revision: str | Sequence[str] | None = "9ab1f891554a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "research_conversations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
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
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_research_conversations_owner_id"),
        "research_conversations",
        ["owner_id"],
        unique=False,
    )

    op.add_column(
        "research_sessions",
        sa.Column("conversation_id", sa.UUID(), nullable=True),
    )
    op.create_index(
        op.f("ix_research_sessions_conversation_id"),
        "research_sessions",
        ["conversation_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_research_sessions_conversation_id_research_conversations",
        "research_sessions",
        "research_conversations",
        ["conversation_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "fk_research_sessions_conversation_id_research_conversations",
        "research_sessions",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_research_sessions_conversation_id"),
        table_name="research_sessions",
    )
    op.drop_column("research_sessions", "conversation_id")

    op.drop_index(
        op.f("ix_research_conversations_owner_id"),
        table_name="research_conversations",
    )
    op.drop_table("research_conversations")
