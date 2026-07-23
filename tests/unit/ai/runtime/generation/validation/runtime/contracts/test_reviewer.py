"""
Unit tests for ReviewerRuntimeContract.

Covers:
- A fully compliant review output is valid, with quality_score reflected as score
- Missing quality_score produces the expected error
- An out-of-range quality_score is an error
- runtime/contract_name/name identity

Field name mirrors `ModelReviewAssessment` (`app/ai/runtime/research/review.py`),
the actual `output_model` the reviewer step requests.
"""

from __future__ import annotations

from app.ai.runtime.generation.validation.runtime.contracts.reviewer import (
    ReviewerRuntimeContract,
)
from app.ai.runtime.generation.validation.runtime.enums import RuntimeType

from tests.unit.ai.runtime.generation.validation.factories import make_result

_COMPLIANT_PAYLOAD = {
    "quality_score": 0.7,
    "gap_questions": [],
    "concerns": ["Light on counterarguments."],
}


async def test_contract_identity() -> None:
    contract = ReviewerRuntimeContract()

    assert contract.runtime == RuntimeType.REVIEWER
    assert contract.contract_name == "reviewer_contract"
    assert contract.name == "reviewer_contract"


async def test_fully_compliant_output_is_valid() -> None:
    contract = ReviewerRuntimeContract()

    result = make_result(parsed_output=dict(_COMPLIANT_PAYLOAD))

    outcome = await contract.validate(result)

    assert outcome.issues == []
    assert outcome.score == 0.7


async def test_missing_requirements_produce_expected_errors() -> None:
    contract = ReviewerRuntimeContract()

    result = make_result(parsed_output={})

    outcome = await contract.validate(result)

    messages = " ".join(issue.message for issue in outcome.issues)

    assert "quality_score" in messages


async def test_out_of_range_quality_score_is_an_error() -> None:
    contract = ReviewerRuntimeContract()

    result = make_result(
        parsed_output={
            "quality_score": 1.5,
            "concerns": ["y"],
        }
    )

    outcome = await contract.validate(result)

    assert any("outside the valid range" in issue.message for issue in outcome.issues)
