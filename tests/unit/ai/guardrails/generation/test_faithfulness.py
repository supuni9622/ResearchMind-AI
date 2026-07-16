"""
Uses the real HallucinationValidator (Validation Platform) rather than a
fake -- it's cheap, deterministic, and this is exactly the composition
this guardrail is responsible for getting right.
"""

from __future__ import annotations

from app.ai.guardrails.enums import GuardrailCategory, GuardrailSeverity
from app.ai.guardrails.generation.faithfulness import FaithfulnessGuardrail
from app.ai.runtime.generation.validation.output.hallucination_validator import (
    HallucinationValidator,
)

from tests.unit.ai.guardrails.factories import make_prompt_context, make_request, make_result


async def test_well_grounded_response_produces_no_issues() -> None:
    guardrail = FaithfulnessGuardrail(HallucinationValidator())

    context = "Photosynthesis converts sunlight chlorophyll glucose oxygen carbon dioxide water."
    request = make_request(prompt_context=make_prompt_context(context=context))
    result = make_result(request=request, content=context)

    issues = await guardrail.check(result)

    assert issues == []


async def test_ungrounded_response_errors() -> None:
    guardrail = FaithfulnessGuardrail(HallucinationValidator())

    context = "Photosynthesis converts sunlight chlorophyll glucose oxygen carbon dioxide water."
    request = make_request(prompt_context=make_prompt_context(context=context))
    result = make_result(
        request=request,
        content="Bicycle mechanics require chain tension adjustments regularly indeed always.",
    )

    issues = await guardrail.check(result)

    assert len(issues) == 1
    assert issues[0].severity == GuardrailSeverity.ERROR
    assert issues[0].category == GuardrailCategory.FAITHFULNESS


async def test_no_context_produces_no_issues() -> None:
    guardrail = FaithfulnessGuardrail(HallucinationValidator())

    result = make_result(request=make_request(prompt_context=make_prompt_context(context="")))

    issues = await guardrail.check(result)

    assert issues == []
