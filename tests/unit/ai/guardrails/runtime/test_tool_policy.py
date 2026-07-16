from __future__ import annotations

from app.ai.guardrails.runtime.tool_policy import (
    AllowAllToolPolicyProvider,
    ToolPolicyGuardrail,
    ToolPolicyProvider,
)

from tests.unit.ai.guardrails.factories import make_budget_policy, make_execution_state


async def test_allow_all_provider_never_flags() -> None:
    guardrail = ToolPolicyGuardrail(
        AllowAllToolPolicyProvider(), attempted_tool_names=["web_search", "execute_code"]
    )

    issues = await guardrail.check(make_execution_state(), make_budget_policy())

    assert issues == []


async def test_no_attempted_tools_produces_no_issues() -> None:
    guardrail = ToolPolicyGuardrail(AllowAllToolPolicyProvider())

    issues = await guardrail.check(make_execution_state(), make_budget_policy())

    assert issues == []


class _DenyListProvider(ToolPolicyProvider):
    def __init__(self, denied: set[str]) -> None:
        self._denied = denied

    def is_allowed(self, tool_name: str) -> bool:
        return tool_name not in self._denied


async def test_denied_tool_errors() -> None:
    guardrail = ToolPolicyGuardrail(
        _DenyListProvider({"execute_code"}), attempted_tool_names=["web_search", "execute_code"]
    )

    issues = await guardrail.check(make_execution_state(), make_budget_policy())

    assert len(issues) == 1
    assert issues[0].metadata["tool_name"] == "execute_code"
