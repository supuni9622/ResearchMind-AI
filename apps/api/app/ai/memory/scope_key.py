"""Shared scope-to-key-segment mapping, used everywhere a memory scope is
embedded into a Valkey key (session store, interest promotion, durable
availability). One place for the explicit 3-way branch -- a binary
`"personal" if PERSONAL else f"project:{project_id}"` ternary silently
produces the broken segment `"project:None"` for GLOBAL (project_id is
always None for GLOBAL, same as PERSONAL)."""

from __future__ import annotations

from uuid import UUID

from app.ai.memory.enums import MemoryScopeType


def scope_key(scope_type: MemoryScopeType, project_id: UUID | None) -> str:
    if scope_type == MemoryScopeType.PERSONAL:
        return "personal"
    if scope_type == MemoryScopeType.GLOBAL:
        return "global"
    return f"project:{project_id}"
