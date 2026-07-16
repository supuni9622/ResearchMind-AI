from __future__ import annotations

from app.ai.guardrails.policies.runtime_policy import RuntimePolicy


def test_default_stops_on_budget_violation() -> None:
    assert RuntimePolicy().stop_on_budget_violation is True


def test_can_be_disabled() -> None:
    assert RuntimePolicy(stop_on_budget_violation=False).stop_on_budget_violation is False
