"""
Unit tests for HallucinationValidator.

Covers:
- No context to ground against -> no-op
- Response too short to score meaningfully -> no-op
- Well-grounded response (high lexical overlap) -> no issues, high score
- Poorly-grounded response (low lexical overlap) -> WARNING, low score
"""

from __future__ import annotations

from app.ai.runtime.generation.validation.models import ValidationSeverity
from app.ai.runtime.generation.validation.output.hallucination_validator import (
    HallucinationValidator,
)

from tests.unit.ai.runtime.generation.validation.factories import (
    make_prompt_context,
    make_request,
    make_result,
)

validator = HallucinationValidator()


async def test_validate_is_a_noop_when_no_context() -> None:
    result = make_result(
        request=make_request(prompt_context=make_prompt_context(context="")),
        content="Completely unrelated made-up claims about distant galaxies.",
    )

    outcome = await validator.validate(result)

    assert outcome.issues == []
    assert outcome.score is None


async def test_validate_is_a_noop_when_response_too_short() -> None:
    context = make_prompt_context(
        context="Photosynthesis converts sunlight into chemical energy in plants.",
    )

    result = make_result(
        request=make_request(prompt_context=context),
        content="Yes.",
    )

    outcome = await validator.validate(result)

    assert outcome.issues == []
    assert outcome.score is None


async def test_validate_scores_well_grounded_response_highly() -> None:
    context = make_prompt_context(
        context=(
            "Photosynthesis converts sunlight into chemical energy stored in "
            "glucose molecules inside plant chloroplasts."
        ),
    )

    result = make_result(
        request=make_request(prompt_context=context),
        content=(
            "Photosynthesis converts sunlight into chemical energy stored "
            "inside plant chloroplasts."
        ),
    )

    outcome = await validator.validate(result)

    assert outcome.issues == []
    assert outcome.score is not None
    assert outcome.score >= 0.3


async def test_validate_warns_on_poorly_grounded_response() -> None:
    context = make_prompt_context(
        context="Photosynthesis converts sunlight into chemical energy in plants.",
    )

    result = make_result(
        request=make_request(prompt_context=context),
        content=(
            "Ancient volcanic eruptions reshaped continental drift patterns "
            "across geological timescales entirely."
        ),
    )

    outcome = await validator.validate(result)

    assert len(outcome.issues) == 1
    assert outcome.issues[0].severity == ValidationSeverity.WARNING
    assert outcome.score is not None
    assert outcome.score < 0.3
