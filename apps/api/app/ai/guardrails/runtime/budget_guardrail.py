from __future__ import annotations

from app.ai.guardrails.constants import BUDGET_WARN_MARGIN
from app.ai.guardrails.enums import GuardrailCategory, GuardrailSeverity
from app.ai.guardrails.interfaces import RuntimeGuardrailInterface
from app.ai.guardrails.models import GuardrailIssue
from app.ai.guardrails.runtime.execution_limits import BudgetPolicy, ExecutionState

_LIMITS: tuple[tuple[str, str, str], ...] = (
    ("tokens_used", "max_tokens", "tokens"),
    ("cost_usd", "max_cost_usd", "cost (USD)"),
    ("tool_calls_made", "max_tool_calls", "tool calls"),
    ("iterations_completed", "max_iterations", "iterations"),
    ("elapsed_seconds", "max_runtime_seconds", "seconds"),
)
"""(state attribute, policy attribute, human label) for each of the five
PRD §11 budget dimensions -- checked identically, so this table drives
one loop instead of five near-duplicate `if` blocks."""


class BudgetGuardrail(
    RuntimeGuardrailInterface,
):
    """
    Runtime budget enforcement (PRD §11, P1 -- "implement immediately"):
    max_tokens/max_cost/max_tool_calls/max_iterations/max_runtime_seconds.
    A `None` limit on `BudgetPolicy` means that dimension is unbounded.
    """

    @property
    def name(
        self,
    ) -> str:
        return "budget_guardrail"

    async def check(
        self,
        state: ExecutionState,
        policy: BudgetPolicy,
    ) -> list[GuardrailIssue]:

        issues: list[GuardrailIssue] = []

        for state_attr, policy_attr, label in _LIMITS:
            limit = getattr(policy, policy_attr)

            if limit is None:
                continue

            used = getattr(state, state_attr)

            if used > limit:
                issues.append(
                    GuardrailIssue(
                        code=f"{policy_attr}_exceeded",
                        severity=GuardrailSeverity.ERROR,
                        category=GuardrailCategory.BUDGET,
                        message=f"Used {used} {label}, exceeding the limit of {limit}.",
                        metadata={"used": used, "limit": limit},
                    )
                )
            elif limit > 0 and used >= limit * BUDGET_WARN_MARGIN:
                issues.append(
                    GuardrailIssue(
                        code=f"{policy_attr}_near_limit",
                        severity=GuardrailSeverity.WARNING,
                        category=GuardrailCategory.BUDGET,
                        message=(
                            f"Used {used} {label}, at {used / limit:.0%} of the limit ({limit})."
                        ),
                        metadata={"used": used, "limit": limit},
                    )
                )

        return issues
