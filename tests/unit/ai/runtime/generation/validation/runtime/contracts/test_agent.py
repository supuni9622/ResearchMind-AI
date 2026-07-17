"""
Unit tests for AgentRuntimeContract.

Covers:
- A fully compliant agent output is valid with no issues
- Missing reasoning/completion_state/tool_trace produce the expected errors
- runtime/contract_name/name identity
"""

from __future__ import annotations

from app.ai.runtime.generation.validation.runtime.contracts.agent import (
    AgentRuntimeContract,
)
from app.ai.runtime.generation.validation.runtime.enums import RuntimeType

from tests.unit.ai.runtime.generation.validation.factories import make_result

_COMPLIANT_PAYLOAD = {
    "reasoning": "Searched the knowledge base, then summarized the top result.",
    "completion_state": "completed",
    "tool_trace": [{"tool": "search", "input": "query", "output": "result"}],
}


async def test_contract_identity() -> None:
    contract = AgentRuntimeContract()

    assert contract.runtime == RuntimeType.AGENT
    assert contract.contract_name == "agent_contract"
    assert contract.name == "agent_contract"


async def test_fully_compliant_output_is_valid() -> None:
    contract = AgentRuntimeContract()

    result = make_result(parsed_output=dict(_COMPLIANT_PAYLOAD))

    outcome = await contract.validate(result)

    assert outcome.issues == []


async def test_missing_requirements_produce_expected_errors() -> None:
    contract = AgentRuntimeContract()

    result = make_result(parsed_output={})

    outcome = await contract.validate(result)

    messages = " ".join(issue.message for issue in outcome.issues)

    assert "reasoning" in messages
    assert "completion_state" in messages
    assert "tool_trace" in messages


async def test_every_issue_is_tagged_with_the_contract_name() -> None:
    contract = AgentRuntimeContract()

    result = make_result(parsed_output={})

    outcome = await contract.validate(result)

    assert outcome.issues
    assert all(issue.validator == "agent_contract" for issue in outcome.issues)
