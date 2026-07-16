"""
Unit tests for JsonValidator.

Covers:
- JSON not expected (plain text response_format, no schema) -> no-op
- Valid JSON content -> no issues, score 1.0
- JSON expected via output_schema alone (TEXT format) -> still checked
- Repairable JSON (markdown code fence wrapping) -> WARNING, score 0.5
- Unparseable/unrepairable content -> ERROR, score 0.0
"""

from __future__ import annotations

from app.ai.runtime.generation.enums import ResponseFormat
from app.ai.runtime.generation.validation.models import ValidationSeverity
from app.ai.runtime.generation.validation.output.json_validator import JsonValidator

from tests.unit.ai.runtime.generation.validation.factories import make_request, make_result

validator = JsonValidator()


async def test_validate_is_a_noop_when_json_not_expected() -> None:
    result = make_result(
        request=make_request(response_format=ResponseFormat.TEXT, output_schema=None),
        content="not json at all, just prose.",
    )

    outcome = await validator.validate(result)

    assert outcome.issues == []
    assert outcome.score is None


async def test_validate_scores_valid_json_as_one() -> None:
    result = make_result(
        request=make_request(response_format=ResponseFormat.JSON),
        content='{"answer": "blue"}',
    )

    outcome = await validator.validate(result)

    assert outcome.issues == []
    assert outcome.score == 1.0


async def test_validate_runs_when_only_output_schema_is_set() -> None:
    result = make_result(
        request=make_request(
            response_format=ResponseFormat.TEXT,
            output_schema={"type": "object"},
        ),
        content='{"answer": "blue"}',
    )

    outcome = await validator.validate(result)

    assert outcome.score == 1.0


async def test_validate_warns_on_repairable_json() -> None:
    result = make_result(
        request=make_request(response_format=ResponseFormat.JSON),
        content='```json\n{"answer": "blue"}\n```',
    )

    outcome = await validator.validate(result)

    assert len(outcome.issues) == 1
    assert outcome.issues[0].severity == ValidationSeverity.WARNING
    assert outcome.score == 0.5


async def test_validate_errors_on_unparseable_content() -> None:
    result = make_result(
        request=make_request(response_format=ResponseFormat.JSON),
        content="This is just prose, not JSON at all and has no braces.",
    )

    outcome = await validator.validate(result)

    assert len(outcome.issues) == 1
    assert outcome.issues[0].severity == ValidationSeverity.ERROR
    assert outcome.score == 0.0
