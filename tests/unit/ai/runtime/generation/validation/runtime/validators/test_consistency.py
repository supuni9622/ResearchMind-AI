"""
Unit tests for ConsistencyValidator.

Covers:
- An evidence item referencing a real section id has no issue
- An evidence item referencing an unknown section id is an ERROR (orphan reference)
- Missing sections or missing evidence means nothing to check
- Evidence items with no section_id at all are not flagged (that pointer is optional)
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
