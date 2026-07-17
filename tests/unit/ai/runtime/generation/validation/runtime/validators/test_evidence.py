"""
Unit tests for EvidenceValidator.

Covers:
- Evidence items with content and a source pointer have no issue
- An evidence item missing content is a WARNING
- An evidence item missing both citation_id and section_id is a WARNING
- Fewer items than `minimum` is an ERROR
- minimum=0 (the default) never flags the count, only per-item quality
- No `evidence` field at all means nothing to check
"""

from __future__ import annotations

from app.ai.runtime.generation.validation.models import ValidationSeverity
from app.ai.runtime.generation.validation.runtime.validators.evidence import (
    EvidenceValidator,
)

from tests.unit.ai.runtime.generation.validation.factories import make_result


async def test_well_formed_evidence_has_no_issues() -> None:
    validator = EvidenceValidator()

    result = make_result(
        parsed_output={"evidence": [{"content": "supports the claim", "citation_id": "S1"}]}
    )

    outcome = await validator.validate(result)

    assert outcome.issues == []


async def test_evidence_missing_content_is_a_warning() -> None:
    validator = EvidenceValidator()

    result = make_result(parsed_output={"evidence": [{"content": "", "citation_id": "S1"}]})

    outcome = await validator.validate(result)

    assert len(outcome.issues) == 1
    assert outcome.issues[0].severity == ValidationSeverity.WARNING


async def test_evidence_missing_source_pointer_is_a_warning() -> None:
    validator = EvidenceValidator()

    result = make_result(parsed_output={"evidence": [{"content": "supports the claim"}]})

    outcome = await validator.validate(result)

    assert len(outcome.issues) == 1
    assert outcome.issues[0].severity == ValidationSeverity.WARNING


async def test_too_few_evidence_items_is_an_error_when_minimum_set() -> None:
    validator = EvidenceValidator(minimum=2)

    result = make_result(parsed_output={"evidence": [{"content": "x", "citation_id": "S1"}]})

    outcome = await validator.validate(result)

    assert any(issue.severity == ValidationSeverity.ERROR for issue in outcome.issues)


async def test_default_minimum_zero_does_not_flag_empty_evidence_count() -> None:
    validator = EvidenceValidator()

    result = make_result(parsed_output={"evidence": []})

    outcome = await validator.validate(result)

    assert outcome.issues == []


async def test_missing_evidence_field_means_nothing_to_check() -> None:
    validator = EvidenceValidator(minimum=1)

    result = make_result(parsed_output={})

    outcome = await validator.validate(result)

    assert outcome.issues == []
