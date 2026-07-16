from __future__ import annotations

from app.ai.guardrails.input.rate_limit import RateLimitGuardrail

from tests.unit.ai.guardrails.factories import make_request


async def test_always_allows() -> None:
    guardrail = RateLimitGuardrail()

    issues = await guardrail.check(make_request())

    assert issues == []
