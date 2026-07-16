from __future__ import annotations

from abc import ABC, abstractmethod

from app.ai.guardrails.enums import GuardrailCategory, GuardrailSeverity
from app.ai.guardrails.interfaces import RuntimeGuardrailInterface
from app.ai.guardrails.models import GuardrailIssue
from app.ai.guardrails.runtime.execution_limits import BudgetPolicy, ExecutionState


class ToolPolicyProvider(
    ABC,
):
    """
    Foundation only (PRD §11) -- future: `allowed_tools`, `denied_tools`,
    tool categories. Seam for a real policy provider once tool-call
    tracking exists on `ExecutionState`.
    """

    @abstractmethod
    def is_allowed(
        self,
        tool_name: str,
    ) -> bool:
        pass


class AllowAllToolPolicyProvider(
    ToolPolicyProvider,
):
    def is_allowed(
        self,
        tool_name: str,
    ) -> bool:

        return True


class ToolPolicyGuardrail(
    RuntimeGuardrailInterface,
):
    """
    Checks any attempted tool calls against the configured provider.
    Effectively a no-op today: `ExecutionState` doesn't yet track which
    tools were actually called, only how many (`tool_calls_made`) --
    the seam exists so a future tool-call log can be checked here
    without changing the registry/service wiring.
    """

    def __init__(
        self,
        provider: ToolPolicyProvider,
        *,
        attempted_tool_names: list[str] | None = None,
    ) -> None:
        self._provider = provider

        self._attempted_tool_names = attempted_tool_names or []

    @property
    def name(
        self,
    ) -> str:
        return "tool_policy"

    async def check(
        self,
        state: ExecutionState,
        policy: BudgetPolicy,
    ) -> list[GuardrailIssue]:

        return [
            GuardrailIssue(
                code="tool_denied",
                severity=GuardrailSeverity.ERROR,
                category=GuardrailCategory.TOOL_POLICY,
                message=f"Tool '{tool_name}' is not permitted by the current tool policy.",
                metadata={"tool_name": tool_name},
            )
            for tool_name in self._attempted_tool_names
            if not self._provider.is_allowed(tool_name)
        ]
