"""
Unit tests for the top-level output ConsistencyValidator.

Covers:
- A valid section reference has no issue
- An orphan section reference is an ERROR
- Issues are tagged with this validator's own name ("consistency"),
  not the delegate's ("runtime_consistency")
"""

from __future__ import annotations

from app.ai.runtime.generation.validation.output.consistency_validator import (
    ConsistencyValidator,
)

from tests.unit.ai.runtime.generation.validation.factories import make_result

validator = ConsistencyValidator()


async def test_valid_section_reference_has_no_issue() -> None:
    result = make_result(
        parsed_output={
            "sections": [{"id": "sec-1"}],
            "evidence": [{"content": "x", "section_id": "sec-1"}],
        }
    )

    outcome = await validator.validate(result)

    assert outcome.issues == []


async def test_orphan_section_reference_is_an_error() -> None:
    result = make_result(
        parsed_output={
            "sections": [{"id": "sec-1"}],
            "evidence": [{"content": "x", "section_id": "sec-99"}],
        }
    )

    outcome = await validator.validate(result)

    assert len(outcome.issues) == 1
    assert outcome.issues[0].validator == "consistency"
    assert "sec-99" in outcome.issues[0].message
