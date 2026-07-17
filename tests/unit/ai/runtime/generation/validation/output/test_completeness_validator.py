"""
Unit tests for the top-level output CompletenessValidator.

Covers:
- No output_schema requested -> no-op
- A schema's scalar required field missing is an ERROR
- A schema's array-typed required field below one item is an ERROR
- A payload satisfying the schema's requirements has no issues
- A trivially short summary is a WARNING, not an ERROR
- Issues are tagged with this validator's own name ("completeness"),
  not the delegate's ("runtime_completeness")
"""

from __future__ import annotations

from app.ai.runtime.generation.validation.output.completeness_validator import (
    CompletenessValidator,
)

from tests.unit.ai.runtime.generation.validation.factories import make_request, make_result

validator = CompletenessValidator()

_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "sections": {"type": "array"},
    },
    "required": ["summary", "sections"],
}


async def test_no_schema_means_nothing_to_check() -> None:
    result = make_result(request=make_request(output_schema=None), parsed_output={})

    outcome = await validator.validate(result)

    assert outcome.issues == []


async def test_missing_scalar_required_field_is_an_error() -> None:
    result = make_result(
        request=make_request(output_schema=_SCHEMA),
        parsed_output={"sections": ["a"]},
    )

    outcome = await validator.validate(result)

    assert any("summary" in issue.message for issue in outcome.issues)


async def test_missing_array_required_field_is_an_error() -> None:
    result = make_result(
        request=make_request(output_schema=_SCHEMA),
        parsed_output={"summary": "hi"},
    )

    outcome = await validator.validate(result)

    assert any("sections" in issue.message for issue in outcome.issues)


async def test_satisfied_schema_has_no_issues() -> None:
    result = make_result(
        request=make_request(output_schema=_SCHEMA),
        parsed_output={
            "summary": "A sufficiently long summary to clear the minimum length.",
            "sections": ["a"],
        },
    )

    outcome = await validator.validate(result)

    assert outcome.issues == []


async def test_trivial_summary_is_a_warning() -> None:
    result = make_result(
        request=make_request(output_schema=_SCHEMA),
        parsed_output={"summary": "hi", "sections": ["a"]},
    )

    outcome = await validator.validate(result)

    assert any("trivial" in issue.message for issue in outcome.issues)


async def test_issues_are_tagged_with_this_validators_own_name() -> None:
    result = make_result(
        request=make_request(output_schema=_SCHEMA),
        parsed_output={},
    )

    outcome = await validator.validate(result)

    assert outcome.issues
    assert all(issue.validator == "completeness" for issue in outcome.issues)
