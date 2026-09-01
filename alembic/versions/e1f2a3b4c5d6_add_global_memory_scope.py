"""add global memory scope

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-09-01 00:00:00.000000

Adds a third `scope_type` value, GLOBAL, alongside personal/project.
GLOBAL rows always have `project_id IS NULL` (same shape as personal),
so the two check constraints below gain a third OR-arm rather than
being restructured.

Also fixes a real pre-existing bug: `uq_memory_scope_settings_personal`
was `UNIQUE(owner_id) WHERE project_id IS NULL`, not qualified by
`scope_type` -- a GLOBAL settings row (also `project_id IS NULL`) would
collide with the owner's PERSONAL row on that index. Recreated as
`UNIQUE(owner_id, scope_type) WHERE project_id IS NULL`.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e1f2a3b4c5d6"
down_revision: str | Sequence[str] | None = "d0e1f2a3b4c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_MEMORIES_OLD = (
    "(scope_type = 'personal' AND project_id IS NULL) OR "
    "(scope_type = 'project' AND project_id IS NOT NULL)"
)
_MEMORIES_NEW = (
    "(scope_type = 'personal' AND project_id IS NULL) OR "
    "(scope_type = 'global' AND project_id IS NULL) OR "
    "(scope_type = 'project' AND project_id IS NOT NULL)"
)


def upgrade() -> None:
    op.drop_constraint("ck_memories_scope_project", "memories", type_="check")
    op.create_check_constraint("ck_memories_scope_project", "memories", _MEMORIES_NEW)

    op.drop_constraint(
        "ck_memory_scope_settings_scope_project", "memory_scope_settings", type_="check"
    )
    op.create_check_constraint(
        "ck_memory_scope_settings_scope_project", "memory_scope_settings", _MEMORIES_NEW
    )

    op.drop_index("uq_memory_scope_settings_personal", table_name="memory_scope_settings")
    op.create_index(
        "uq_memory_scope_settings_personal",
        "memory_scope_settings",
        ["owner_id", "scope_type"],
        unique=True,
        postgresql_where=sa.text("project_id IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_memory_scope_settings_personal", table_name="memory_scope_settings")
    op.create_index(
        "uq_memory_scope_settings_personal",
        "memory_scope_settings",
        ["owner_id"],
        unique=True,
        postgresql_where=sa.text("project_id IS NULL"),
    )

    op.drop_constraint(
        "ck_memory_scope_settings_scope_project", "memory_scope_settings", type_="check"
    )
    op.create_check_constraint(
        "ck_memory_scope_settings_scope_project", "memory_scope_settings", _MEMORIES_OLD
    )

    op.drop_constraint("ck_memories_scope_project", "memories", type_="check")
    op.create_check_constraint("ck_memories_scope_project", "memories", _MEMORIES_OLD)
