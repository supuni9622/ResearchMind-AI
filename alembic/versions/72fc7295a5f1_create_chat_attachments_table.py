"""create chat_attachments table

Revision ID: 72fc7295a5f1
Revises: dfffb70dfaa8
Create Date: 2026-09-02 00:00:00.000000

Backs Wave 4 Phase 1 (chat image attachments, up to 5/turn,
docs/PRIORITIZED_ROADMAP.md). Deliberately separate from `documents` --
these images are handed to a vision-capable provider as a presigned URL,
not RAG-indexed (no chunking/embedding/Qdrant). `conversation_id`/
`message_id` start NULL: a client uploads an image before the turn is
sent, and before a brand-new conversation even exists.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "72fc7295a5f1"
down_revision: str | Sequence[str] | None = "dfffb70dfaa8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chat_attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index("ix_chat_attachments_owner_id", "chat_attachments", ["owner_id"])
    op.create_index("ix_chat_attachments_conversation_id", "chat_attachments", ["conversation_id"])
    op.create_index("ix_chat_attachments_message_id", "chat_attachments", ["message_id"])


def downgrade() -> None:
    op.drop_index("ix_chat_attachments_message_id", table_name="chat_attachments")
    op.drop_index("ix_chat_attachments_conversation_id", table_name="chat_attachments")
    op.drop_index("ix_chat_attachments_owner_id", table_name="chat_attachments")
    op.drop_table("chat_attachments")
