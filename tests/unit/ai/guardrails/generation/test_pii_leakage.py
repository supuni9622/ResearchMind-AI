from __future__ import annotations

from app.ai.guardrails.enums import GuardrailCategory, GuardrailSeverity
from app.ai.guardrails.generation.pii_leakage import PiiLeakageGuardrail

from tests.unit.ai.guardrails.factories import make_result


async def test_clean_response_produces_no_issues() -> None:
    guardrail = PiiLeakageGuardrail()

    issues = await guardrail.check(make_result(content="The sky is blue."))

    assert issues == []


async def test_email_in_response_warns() -> None:
    guardrail = PiiLeakageGuardrail()

    issues = await guardrail.check(make_result(content="Contact us at support@example.com."))

    assert len(issues) == 1
    assert issues[0].severity == GuardrailSeverity.WARNING
    assert issues[0].category == GuardrailCategory.PII
