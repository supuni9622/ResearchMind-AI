"""
Unit tests for MCPRuntimeContract.

Covers:
- A fully compliant MCP output is valid with no issues
- Missing tool_outputs/execution_metadata produce the expected errors
- A tool_reference pointing at an unknown tool_call_id is an error
- runtime/contract_name/name identity
"""

from __future__ import annotations

from app.ai.runtime.generation.validation.runtime.contracts.mcp import (
    MCPRuntimeContract,
)
from app.ai.runtime.generation.validation.runtime.enums import RuntimeType

from tests.unit.ai.runtime.generation.validation.factories import make_result

_COMPLIANT_PAYLOAD = {
    "tool_outputs": [{"id": "call-1", "result": "42"}],
    "tool_references": [{"tool_call_id": "call-1"}],
    "execution_metadata": {"duration_ms": 120},
}


async def test_contract_identity() -> None:
    contract = MCPRuntimeContract()

    assert contract.runtime == RuntimeType.MCP
    assert contract.contract_name == "mcp_contract"
    assert contract.name == "mcp_contract"


async def test_fully_compliant_output_is_valid() -> None:
    contract = MCPRuntimeContract()

    result = make_result(parsed_output=dict(_COMPLIANT_PAYLOAD))

    outcome = await contract.validate(result)

    assert outcome.issues == []


async def test_missing_requirements_produce_expected_errors() -> None:
    contract = MCPRuntimeContract()

    result = make_result(parsed_output={})

    outcome = await contract.validate(result)

    messages = " ".join(issue.message for issue in outcome.issues)

    assert "tool_outputs" in messages
    assert "execution_metadata" in messages


async def test_unknown_tool_reference_is_an_error() -> None:
    contract = MCPRuntimeContract()

    result = make_result(
        parsed_output={
            "tool_outputs": [{"id": "call-1"}],
            "tool_references": [{"tool_call_id": "call-unknown"}],
            "execution_metadata": {"duration_ms": 10},
        }
    )

    outcome = await contract.validate(result)

    assert any("call-unknown" in issue.message for issue in outcome.issues)
