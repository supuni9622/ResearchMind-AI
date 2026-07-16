"""
Unit tests for SchemaValidator.

Covers:
- No schema requested -> no-op
- Schema requested but parsed_output missing -> ERROR
- parsed_output matches schema -> no issues, valid
- parsed_output violates schema -> ERROR with path details
- parsed_output is a BaseModel instance -> dumped before validation
- output_schema itself malformed -> WARNING (SchemaError), not ERROR
"""

from __future__ import annotations

from app.ai.runtime.generation.validation.models import ValidationSeverity
from app.ai.runtime.generation.validation.output.schema_validator import SchemaValidator
from pydantic import BaseModel

from tests.unit.ai.runtime.generation.validation.factories import make_request, make_result

validator = SchemaValidator()

_SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "string"}},
    "required": ["answer"],
}


async def test_validate_returns_empty_outcome_when_no_schema_requested() -> None:
    result = make_result(request=make_request(output_schema=None))

    outcome = await validator.validate(result)

    assert outcome.issues == []
    assert outcome.score is None


async def test_validate_errors_when_schema_requested_but_no_parsed_output() -> None:
    result = make_result(
        request=make_request(output_schema=_SCHEMA),
        parsed_output=None,
    )

    outcome = await validator.validate(result)

    assert len(outcome.issues) == 1
    assert outcome.issues[0].severity == ValidationSeverity.ERROR
    assert "no parsed_output" in outcome.issues[0].message


async def test_validate_passes_when_parsed_output_matches_schema() -> None:
    result = make_result(
        request=make_request(output_schema=_SCHEMA),
        parsed_output={"answer": "blue"},
    )

    outcome = await validator.validate(result)

    assert outcome.issues == []


async def test_validate_errors_when_parsed_output_violates_schema() -> None:
    result = make_result(
        request=make_request(output_schema=_SCHEMA),
        parsed_output={"wrong_field": "blue"},
    )

    outcome = await validator.validate(result)

    assert len(outcome.issues) == 1
    assert outcome.issues[0].severity == ValidationSeverity.ERROR
    assert outcome.issues[0].details["path"] == []


async def test_validate_dumps_pydantic_model_before_checking_schema() -> None:
    class Answer(BaseModel):
        answer: str

    result = make_result(
        request=make_request(output_schema=_SCHEMA),
        parsed_output=Answer(answer="blue"),
    )

    outcome = await validator.validate(result)

    assert outcome.issues == []


async def test_validate_warns_when_output_schema_itself_is_invalid() -> None:
    malformed_schema = {"type": "not-a-real-type"}

    result = make_result(
        request=make_request(output_schema=malformed_schema),
        parsed_output={"answer": "blue"},
    )

    outcome = await validator.validate(result)

    assert len(outcome.issues) == 1
    assert outcome.issues[0].severity == ValidationSeverity.WARNING
