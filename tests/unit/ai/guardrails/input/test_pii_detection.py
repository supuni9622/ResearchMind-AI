from __future__ import annotations

from app.ai.guardrails.enums import GuardrailCategory, GuardrailSeverity
from app.ai.guardrails.input.pii_detection import PiiDetectionGuardrail

from tests.unit.ai.guardrails.factories import make_request


async def test_clean_prompt_produces_no_issues() -> None:
    guardrail = PiiDetectionGuardrail()

    issues = await guardrail.check(make_request(user_prompt="What is the capital of France?"))

    assert issues == []


async def test_email_in_prompt_warns() -> None:
    guardrail = PiiDetectionGuardrail()

    issues = await guardrail.check(
        make_request(user_prompt="My email is jane@example.com, can you summarize this?")
    )

    assert len(issues) == 1
    assert issues[0].severity == GuardrailSeverity.WARNING
    assert issues[0].category == GuardrailCategory.PII
    assert "email" in issues[0].metadata["pii_types"]
