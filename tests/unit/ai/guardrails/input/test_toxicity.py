from __future__ import annotations

from app.ai.guardrails.input.toxicity import ToxicityGuardrail

from tests.unit.ai.guardrails.factories import make_request


async def test_always_allows() -> None:
    guardrail = ToxicityGuardrail()

    issues = await guardrail.check(make_request())

    assert issues == []
