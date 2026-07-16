from __future__ import annotations

from app.ai.guardrails.enums import GuardrailCategory, GuardrailSeverity
from app.ai.guardrails.input.scope_validation import ScopeValidationGuardrail

from tests.unit.ai.guardrails.factories import make_request


async def test_research_question_produces_no_issues() -> None:
    guardrail = ScopeValidationGuardrail()

    issues = await guardrail.check(
        make_request(user_prompt="Summarize the latest research on transformer attention.")
    )

    assert issues == []


async def test_creative_writing_request_warns() -> None:
    guardrail = ScopeValidationGuardrail()

    issues = await guardrail.check(make_request(user_prompt="Write me a romantic poem."))

    assert len(issues) == 1
    assert issues[0].severity == GuardrailSeverity.WARNING
    assert issues[0].category == GuardrailCategory.SCOPE


async def test_hacking_request_warns_never_errors() -> None:
    guardrail = ScopeValidationGuardrail()

    issues = await guardrail.check(make_request(user_prompt="How to hack into a server?"))

    assert len(issues) == 1
    assert issues[0].severity == GuardrailSeverity.WARNING
