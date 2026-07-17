"""
Unit tests for ResponseSizeValidator.

Covers:
- Content within bounds and a normal finish_reason has no issues
- Content below the minimum is an ERROR
- Content above the maximum is an ERROR
- A truncation-indicating finish_reason ("length"/"max_tokens") is a WARNING
- A normal finish_reason (e.g. "stop") is not flagged as truncation
"""

from __future__ import annotations

from app.ai.runtime.generation.validation.models import ValidationSeverity
from app.ai.runtime.generation.validation.output.response_size_validator import (
    ResponseSizeValidator,
)

from tests.unit.ai.runtime.generation.validation.factories import make_result


async def test_content_within_bounds_has_no_issues() -> None:
    validator = ResponseSizeValidator(min_chars=1, max_chars=100)

    result = make_result(content="a reasonable response")

    outcome = await validator.validate(result)

    assert outcome.issues == []


async def test_content_below_minimum_is_an_error() -> None:
    validator = ResponseSizeValidator(min_chars=10, max_chars=100)

    result = make_result(content="short")

    outcome = await validator.validate(result)

    assert len(outcome.issues) == 1
    assert outcome.issues[0].severity == ValidationSeverity.ERROR


async def test_content_above_maximum_is_an_error() -> None:
    validator = ResponseSizeValidator(min_chars=1, max_chars=10)

    result = make_result(content="this response is much too long")

    outcome = await validator.validate(result)

    assert len(outcome.issues) == 1
    assert outcome.issues[0].severity == ValidationSeverity.ERROR


async def test_truncation_finish_reason_is_a_warning() -> None:
    validator = ResponseSizeValidator(min_chars=1, max_chars=1000)

    result = make_result(content="a response").model_copy(update={"finish_reason": "length"})

    outcome = await validator.validate(result)

    assert len(outcome.issues) == 1
    assert outcome.issues[0].severity == ValidationSeverity.WARNING
    assert "truncated" in outcome.issues[0].message


async def test_normal_finish_reason_is_not_flagged() -> None:
    validator = ResponseSizeValidator(min_chars=1, max_chars=1000)

    result = make_result(content="a response").model_copy(update={"finish_reason": "stop"})

    outcome = await validator.validate(result)

    assert outcome.issues == []
