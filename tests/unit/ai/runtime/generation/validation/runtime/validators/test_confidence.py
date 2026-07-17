"""
Unit tests for ConfidenceValidator.

Covers:
- A confidence within [0, 1] contributes it as the outcome's score
- Out-of-range confidence is an ERROR
- Non-numeric confidence is an ERROR
- A bool confidence is rejected (bool is a subclass of int in Python)
- No confidence field at all means nothing to check
"""

from __future__ import annotations

from app.ai.runtime.generation.validation.models import ValidationSeverity
from app.ai.runtime.generation.validation.runtime.validators.confidence import (
    ConfidenceValidator,
)

from tests.unit.ai.runtime.generation.validation.factories import make_result


async def test_valid_confidence_contributes_its_value_as_score() -> None:
    validator = ConfidenceValidator()

    result = make_result(parsed_output={"confidence": 0.75})

    outcome = await validator.validate(result)

    assert outcome.issues == []
    assert outcome.score == 0.75


async def test_out_of_range_confidence_is_an_error() -> None:
    validator = ConfidenceValidator()

    result = make_result(parsed_output={"confidence": 1.5})

    outcome = await validator.validate(result)

    assert len(outcome.issues) == 1
    assert outcome.issues[0].severity == ValidationSeverity.ERROR


async def test_non_numeric_confidence_is_an_error() -> None:
    validator = ConfidenceValidator()

    result = make_result(parsed_output={"confidence": "high"})

    outcome = await validator.validate(result)

    assert len(outcome.issues) == 1
    assert outcome.issues[0].severity == ValidationSeverity.ERROR


async def test_bool_confidence_is_rejected() -> None:
    validator = ConfidenceValidator()

    result = make_result(parsed_output={"confidence": True})

    outcome = await validator.validate(result)

    assert len(outcome.issues) == 1
    assert outcome.issues[0].severity == ValidationSeverity.ERROR


async def test_missing_confidence_means_nothing_to_check() -> None:
    validator = ConfidenceValidator()

    result = make_result(parsed_output={})

    outcome = await validator.validate(result)

    assert outcome.issues == []
    assert outcome.score is None
