"""
Unit tests for CompletenessValidator.

Covers:
- A payload satisfying every required_fields/list_minimums produces no issues
- A missing scalar required field produces an ERROR
- A list field below its minimum produces an ERROR with the actual/minimum counts
- A falsy-but-present scalar (0) is not treated as missing
- A too-short summary produces a WARNING, not an ERROR
- No configuration at all means nothing to check
"""

from __future__ import annotations

from app.ai.runtime.generation.validation.models import ValidationSeverity
from app.ai.runtime.generation.validation.runtime.validators.completeness import (
    CompletenessValidator,
)

from tests.unit.ai.runtime.generation.validation.factories import make_result


async def test_fully_satisfied_payload_has_no_issues() -> None:
    validator = CompletenessValidator(
        required_fields=["summary", "confidence"],
        list_minimums={"sections": 2, "citations": 1},
        min_summary_length=5,
    )

    result = make_result(
        parsed_output={
            "summary": "A sufficiently long summary.",
            "confidence": 0.5,
            "sections": ["a", "b"],
            "citations": ["S1"],
        }
    )

    outcome = await validator.validate(result)

    assert outcome.issues == []


async def test_missing_scalar_required_field_is_an_error() -> None:
    validator = CompletenessValidator(required_fields=["confidence"])

    result = make_result(parsed_output={"summary": "hi"})

    outcome = await validator.validate(result)

    assert len(outcome.issues) == 1
    assert outcome.issues[0].severity == ValidationSeverity.ERROR
    assert "confidence" in outcome.issues[0].message


async def test_list_field_below_minimum_is_an_error() -> None:
    validator = CompletenessValidator(list_minimums={"citations": 2})

    result = make_result(parsed_output={"citations": ["S1"]})

    outcome = await validator.validate(result)

    assert len(outcome.issues) == 1
    assert outcome.issues[0].severity == ValidationSeverity.ERROR
    assert outcome.issues[0].details == {"field": "citations", "minimum": 2, "actual": 1}


async def test_zero_confidence_is_not_treated_as_missing() -> None:
    validator = CompletenessValidator(required_fields=["confidence"])

    result = make_result(parsed_output={"confidence": 0})

    outcome = await validator.validate(result)

    assert outcome.issues == []


async def test_short_summary_is_a_warning() -> None:
    validator = CompletenessValidator(required_fields=["summary"], min_summary_length=50)

    result = make_result(parsed_output={"summary": "too short"})

    outcome = await validator.validate(result)

    assert len(outcome.issues) == 1
    assert outcome.issues[0].severity == ValidationSeverity.WARNING


async def test_no_configuration_means_nothing_to_check() -> None:
    validator = CompletenessValidator()

    result = make_result(parsed_output={"summary": "x"})

    outcome = await validator.validate(result)

    assert outcome.issues == []
