"""
Unit tests for ReviewerRuntimeContract.

Covers:
- A fully compliant review output is valid, with confidence reflected as score
- Missing critique/confidence/recommendations produce the expected errors
- An out-of-range confidence is an error
- runtime/contract_name/name identity
"""

from __future__ import annotations

from app.ai.runtime.generation.validation.runtime.contracts.reviewer import (
    ReviewerRuntimeContract,
)
from app.ai.runtime.generation.validation.runtime.enums import RuntimeType

from tests.unit.ai.runtime.generation.validation.factories import make_result

_COMPLIANT_PAYLOAD = {
    "critique": "The report is well-sourced but light on counterarguments.",
    "confidence": 0.7,
    "recommendations": ["Add a section addressing opposing viewpoints."],
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

    assert "critique" in messages
    assert "confidence" in messages
    assert "recommendations" in messages


async def test_out_of_range_confidence_is_an_error() -> None:
    contract = ReviewerRuntimeContract()

    result = make_result(
        parsed_output={
            "critique": "x",
            "confidence": 1.5,
            "recommendations": ["y"],
        }
    )

    outcome = await contract.validate(result)

    assert any("outside the valid range" in issue.message for issue in outcome.issues)
