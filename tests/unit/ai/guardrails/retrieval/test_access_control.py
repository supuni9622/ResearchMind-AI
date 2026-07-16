from __future__ import annotations

from app.ai.guardrails.retrieval.access_control import (
    AccessControlGuardrail,
    PermissiveAccessControlProvider,
)

from tests.unit.ai.guardrails.factories import make_chunk


async def test_permissive_provider_allows_everything() -> None:
    guardrail = AccessControlGuardrail(PermissiveAccessControlProvider(), owner_id="owner-1")

    issues = await guardrail.check([make_chunk()])

    assert issues == []
