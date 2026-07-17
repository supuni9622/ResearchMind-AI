"""
Unit tests for ConsistencyValidator.

Covers:
- An evidence item referencing a real section id has no issue
- An evidence item referencing an unknown section id is an ERROR (orphan reference)
- Missing sections or missing evidence means nothing to check
- Evidence items with no section_id at all are not flagged (that pointer is optional)
- Custom field names (list_field/id_keys/ref_list_field/ref_key) let the
  same referential-integrity check apply to non-research field shapes
  (e.g. tool_outputs/tool_references)
"""

from __future__ import annotations

from app.ai.runtime.generation.validation.models import ValidationSeverity
from app.ai.runtime.generation.validation.runtime.validators.consistency import (
    ConsistencyValidator,
)

from tests.unit.ai.runtime.generation.validation.factories import make_result


async def test_valid_section_reference_has_no_issue() -> None:
    validator = ConsistencyValidator()

    result = make_result(
        parsed_output={
            "sections": [{"id": "sec-1"}, {"id": "sec-2"}],
            "evidence": [{"content": "x", "section_id": "sec-1"}],
        }
    )

    outcome = await validator.validate(result)

    assert outcome.issues == []


async def test_orphan_section_reference_is_an_error() -> None:
    validator = ConsistencyValidator()

    result = make_result(
        parsed_output={
            "sections": [{"id": "sec-1"}],
            "evidence": [{"content": "x", "section_id": "sec-99"}],
        }
    )

    outcome = await validator.validate(result)

    assert len(outcome.issues) == 1
    assert outcome.issues[0].severity == ValidationSeverity.ERROR
    assert "sec-99" in outcome.issues[0].message


async def test_missing_sections_means_nothing_to_check() -> None:
    validator = ConsistencyValidator()

    result = make_result(parsed_output={"evidence": [{"content": "x", "section_id": "sec-1"}]})

    outcome = await validator.validate(result)

    assert outcome.issues == []


async def test_missing_evidence_means_nothing_to_check() -> None:
    validator = ConsistencyValidator()

    result = make_result(parsed_output={"sections": [{"id": "sec-1"}]})

    outcome = await validator.validate(result)

    assert outcome.issues == []


async def test_evidence_without_a_section_id_is_not_flagged() -> None:
    validator = ConsistencyValidator()

    result = make_result(
        parsed_output={
            "sections": [{"id": "sec-1"}],
            "evidence": [{"content": "x"}],
        }
    )

    outcome = await validator.validate(result)

    assert outcome.issues == []


async def test_custom_field_names_apply_to_non_research_shapes() -> None:
    validator = ConsistencyValidator(
        list_field="tool_outputs",
        id_keys=("id", "tool_call_id"),
        ref_list_field="tool_references",
        ref_key="tool_call_id",
    )

    result = make_result(
        parsed_output={
            "tool_outputs": [{"id": "call-1"}],
            "tool_references": [{"tool_call_id": "call-99"}],
        }
    )

    outcome = await validator.validate(result)

    assert len(outcome.issues) == 1
    assert "call-99" in outcome.issues[0].message


async def test_custom_field_names_with_valid_reference_has_no_issue() -> None:
    validator = ConsistencyValidator(
        list_field="tool_outputs",
        id_keys=("id", "tool_call_id"),
        ref_list_field="tool_references",
        ref_key="tool_call_id",
    )

    result = make_result(
        parsed_output={
            "tool_outputs": [{"id": "call-1"}],
            "tool_references": [{"tool_call_id": "call-1"}],
        }
    )

    outcome = await validator.validate(result)

    assert outcome.issues == []
