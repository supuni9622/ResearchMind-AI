from __future__ import annotations

from app.ai.guardrails.generation.moderation import (
    AlwaysAllowModerationProvider,
    ModerationGuardrail,
)

from tests.unit.ai.guardrails.factories import make_result


async def test_always_allow_provider_produces_no_issues() -> None:
    guardrail = ModerationGuardrail(AlwaysAllowModerationProvider())

    issues = await guardrail.check(make_result(content="anything"))

    assert issues == []
