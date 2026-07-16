"""
Unit tests for TokenBudgetValidator.

Covers:
- No context_window supplied -> no-op (nothing to compare against)
- context_window <= 0 -> no-op (defensive; shouldn't happen but must not
  divide by zero)
- Small prompt, small context window utilization -> no issues, high score
- Prompt + max_tokens comfortably fits -> no issues
- Utilization crosses the warn threshold but still fits -> WARNING
- Estimated tokens exceed context_window -> ERROR, score reflects overflow
"""

from __future__ import annotations

from app.ai.runtime.generation.validation.input.token_budget import TokenBudgetValidator
from app.ai.runtime.generation.validation.models import (
    InputValidationContext,
    ValidationSeverity,
)

from tests.unit.ai.runtime.generation.validation.factories import make_request

validator = TokenBudgetValidator()


async def test_validate_is_a_noop_without_context_window() -> None:
    request = make_request(user_prompt="hello")

    outcome = await validator.validate(request, InputValidationContext(context_window=None))

    assert outcome.issues == []
    assert outcome.score is None


async def test_validate_is_a_noop_for_non_positive_context_window() -> None:
    request = make_request(user_prompt="hello")

    outcome = await validator.validate(request, InputValidationContext(context_window=0))

    assert outcome.issues == []
    assert outcome.score is None


async def test_validate_passes_a_small_prompt_with_large_window() -> None:
    request = make_request(user_prompt="What color is the sky?")

    outcome = await validator.validate(
        request,
        InputValidationContext(context_window=1_000_000),
    )

    assert outcome.issues == []
    assert outcome.score is not None
    assert outcome.score > 0.9


async def test_validate_warns_near_the_context_window_limit() -> None:
    # 5 words -> int(5 * 1.3) = 6 estimated tokens. A context window of
    # 6 puts utilization at 6/6 = 1.0 (>= the 0.9 warn threshold) while
    # still not exceeding the window outright (6 > 6 is False), so this
    # lands in the WARNING branch rather than ERROR.
    request = make_request(user_prompt="one two three four five")

    outcome = await validator.validate(
        request,
        InputValidationContext(context_window=6),
    )

    assert len(outcome.issues) == 1
    assert outcome.issues[0].severity == ValidationSeverity.WARNING


async def test_validate_errors_when_estimated_tokens_exceed_window() -> None:
    request = make_request(
        user_prompt="one two three four five six seven eight nine ten",
        max_tokens=1000,
    )

    outcome = await validator.validate(
        request,
        InputValidationContext(context_window=50),
    )

    assert len(outcome.issues) == 1
    assert outcome.issues[0].severity == ValidationSeverity.ERROR
    assert outcome.score == 0.0
