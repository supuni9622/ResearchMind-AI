"""
Unit tests for PlannerRuntimeContract.

Covers:
- A fully compliant plan output is valid with no issues
- A missing plan/steps produces the expected errors
- An unresolvable step dependency is an error
- runtime/contract_name/name identity
"""

from __future__ import annotations

from app.ai.runtime.generation.validation.runtime.contracts.planner import (
    PlannerRuntimeContract,
)
from app.ai.runtime.generation.validation.runtime.enums import RuntimeType

from tests.unit.ai.runtime.generation.validation.factories import make_result

_COMPLIANT_PAYLOAD = {
    "plan": "Investigate the topic and produce a report.",
    "steps": [
        {"id": "step-1", "depends_on": []},
        {"id": "step-2", "depends_on": ["step-1"]},
    ],
}


async def test_contract_identity() -> None:
    contract = PlannerRuntimeContract()

    assert contract.runtime == RuntimeType.PLANNER
    assert contract.contract_name == "planner_contract"
    assert contract.name == "planner_contract"


async def test_fully_compliant_output_is_valid() -> None:
    contract = PlannerRuntimeContract()

    result = make_result(parsed_output=dict(_COMPLIANT_PAYLOAD))

    outcome = await contract.validate(result)

    assert outcome.issues == []


async def test_missing_plan_and_steps_are_errors() -> None:
    contract = PlannerRuntimeContract()

    result = make_result(parsed_output={})

    outcome = await contract.validate(result)

    messages = " ".join(issue.message for issue in outcome.issues)

    assert "plan" in messages
    assert "steps" in messages


async def test_unresolvable_dependency_is_an_error() -> None:
    contract = PlannerRuntimeContract()

    result = make_result(
        parsed_output={
            "plan": "Investigate the topic.",
            "steps": [{"id": "step-1", "depends_on": ["step-missing"]}],
        }
    )

    outcome = await contract.validate(result)

    assert any("step-missing" in issue.message for issue in outcome.issues)


async def test_every_issue_is_tagged_with_the_contract_name() -> None:
    contract = PlannerRuntimeContract()

    result = make_result(parsed_output={})

    outcome = await contract.validate(result)

    assert outcome.issues
    assert all(issue.validator == "planner_contract" for issue in outcome.issues)
