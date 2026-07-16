from __future__ import annotations

from app.ai.guardrails.runtime.execution_limits import BudgetPolicy, ExecutionState


def test_budget_policy_defaults_are_unbounded() -> None:
    policy = BudgetPolicy()

    assert policy.max_tokens is None
    assert policy.max_cost_usd is None
    assert policy.max_tool_calls is None
    assert policy.max_iterations is None
    assert policy.max_runtime_seconds is None


def test_execution_state_defaults_to_zero() -> None:
    state = ExecutionState()

    assert state.tokens_used == 0
    assert state.cost_usd == 0.0
    assert state.tool_calls_made == 0
    assert state.iterations_completed == 0
    assert state.elapsed_seconds == 0.0
    assert state.visited_state_hashes == []
