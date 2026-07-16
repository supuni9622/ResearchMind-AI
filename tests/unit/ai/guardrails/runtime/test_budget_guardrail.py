from __future__ import annotations

from app.ai.guardrails.enums import GuardrailCategory, GuardrailSeverity
from app.ai.guardrails.runtime.budget_guardrail import BudgetGuardrail

from tests.unit.ai.guardrails.factories import make_budget_policy, make_execution_state


async def test_unbounded_policy_never_flags() -> None:
    guardrail = BudgetGuardrail()

    issues = await guardrail.check(
        make_execution_state(tokens_used=10_000_000), make_budget_policy()
    )

    assert issues == []


async def test_under_budget_produces_no_issues() -> None:
    guardrail = BudgetGuardrail()

    issues = await guardrail.check(
        make_execution_state(tokens_used=10), make_budget_policy(max_tokens=1000)
    )

    assert issues == []


async def test_near_limit_warns() -> None:
    guardrail = BudgetGuardrail()

    issues = await guardrail.check(
        make_execution_state(tokens_used=95), make_budget_policy(max_tokens=100)
    )

    assert len(issues) == 1
    assert issues[0].severity == GuardrailSeverity.WARNING
    assert issues[0].category == GuardrailCategory.BUDGET
    assert issues[0].code == "max_tokens_near_limit"


async def test_over_limit_errors() -> None:
    guardrail = BudgetGuardrail()

    issues = await guardrail.check(
        make_execution_state(tokens_used=150), make_budget_policy(max_tokens=100)
    )

    assert len(issues) == 1
    assert issues[0].severity == GuardrailSeverity.ERROR
    assert issues[0].code == "max_tokens_exceeded"


async def test_checks_all_five_budget_dimensions_independently() -> None:
    guardrail = BudgetGuardrail()

    state = make_execution_state(
        tokens_used=200,
        cost_usd=10.0,
        tool_calls_made=100,
        iterations_completed=50,
        elapsed_seconds=1000.0,
    )
    policy = make_budget_policy(
        max_tokens=100,
        max_cost_usd=5.0,
        max_tool_calls=50,
        max_iterations=25,
        max_runtime_seconds=500.0,
    )

    issues = await guardrail.check(state, policy)

    assert len(issues) == 5
    assert {issue.code for issue in issues} == {
        "max_tokens_exceeded",
        "max_cost_usd_exceeded",
        "max_tool_calls_exceeded",
        "max_iterations_exceeded",
        "max_runtime_seconds_exceeded",
    }
