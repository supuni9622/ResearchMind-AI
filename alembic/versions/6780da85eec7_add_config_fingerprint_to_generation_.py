"""add config fingerprint to generation usage

Revision ID: 6780da85eec7
Revises: 591ddffcd0d7
Create Date: 2026-08-11 01:21:25.163766

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "6780da85eec7"
down_revision: str | Sequence[str] | None = "591ddffcd0d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("generation_usage", sa.Column("surface", sa.String(length=30), nullable=True))
    op.add_column(
        "generation_usage", sa.Column("prompt_version", sa.String(length=50), nullable=True)
    )
    op.add_column(
        "generation_usage", sa.Column("chunking_strategy", sa.String(length=50), nullable=True)
    )
    op.add_column(
        "generation_usage", sa.Column("embedding_model", sa.String(length=100), nullable=True)
    )
    op.add_column("generation_usage", sa.Column("reranker", sa.String(length=50), nullable=True))
    op.add_column(
        "generation_usage", sa.Column("routing_strategy", sa.String(length=30), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("generation_usage", "routing_strategy")
    op.drop_column("generation_usage", "reranker")
    op.drop_column("generation_usage", "embedding_model")
    op.drop_column("generation_usage", "chunking_strategy")
    op.drop_column("generation_usage", "prompt_version")
    op.drop_column("generation_usage", "surface")
