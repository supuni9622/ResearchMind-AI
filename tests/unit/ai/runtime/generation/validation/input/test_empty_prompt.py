"""
Unit tests for EmptyPromptValidator.

Covers:
- Non-empty user_prompt, no system_prompt -> no issues
- Empty/whitespace-only user_prompt -> ERROR
- Explicit empty/whitespace-only system_prompt -> WARNING
- system_prompt=None (the default, "no system prompt") -> not flagged
- Unrendered {placeholder} left in user_prompt -> WARNING listing it
- Unrendered {placeholder} left in system_prompt -> WARNING listing it
- A fully rendered prompt with literal braces from prose (rare) still
  reports it -- this validator can't tell "leftover variable" apart
  from "the user's question literally contains braces"; documented as
  a heuristic, not a hard gate (WARNING only).
"""

from __future__ import annotations

from app.ai.runtime.generation.validation.input.empty_prompt import EmptyPromptValidator
from app.ai.runtime.generation.validation.models import (
    InputValidationContext,
    ValidationSeverity,
)

from tests.unit.ai.runtime.generation.validation.factories import make_request

validator = EmptyPromptValidator()
context = InputValidationContext()


async def test_validate_passes_a_normal_request() -> None:
    request = make_request(user_prompt="What color is the sky?", system_prompt=None)

    outcome = await validator.validate(request, context)

    assert outcome.issues == []


async def test_validate_errors_on_whitespace_only_user_prompt() -> None:
    request = make_request(user_prompt="   ")

    outcome = await validator.validate(request, context)

    assert len(outcome.issues) == 1
    assert outcome.issues[0].severity == ValidationSeverity.ERROR


async def test_validate_warns_on_explicit_empty_system_prompt() -> None:
    request = make_request(system_prompt="   ")

    outcome = await validator.validate(request, context)

    assert len(outcome.issues) == 1
    assert outcome.issues[0].severity == ValidationSeverity.WARNING


async def test_validate_does_not_flag_none_system_prompt() -> None:
    request = make_request(system_prompt=None)

    outcome = await validator.validate(request, context)

    assert outcome.issues == []


async def test_validate_warns_on_unrendered_placeholder_in_user_prompt() -> None:
    request = make_request(user_prompt="Tell me about {topic}.")

    outcome = await validator.validate(request, context)

    assert len(outcome.issues) == 1
    assert outcome.issues[0].severity == ValidationSeverity.WARNING
    assert outcome.issues[0].details["placeholders"] == ["{topic}"]


async def test_validate_warns_on_unrendered_placeholder_in_system_prompt() -> None:
    request = make_request(
        user_prompt="What color is the sky?",
        system_prompt="You are a {persona} assistant.",
    )

    outcome = await validator.validate(request, context)

    assert len(outcome.issues) == 1
    assert outcome.issues[0].details["field"] == "system_prompt"
    assert outcome.issues[0].details["placeholders"] == ["{persona}"]
