"""
Unit tests for `app.ai.runtime.research.planner.prompts`.

Regression: the system prompt previously told the model a single flat
task cap ("no more than five tasks") that didn't match what
`ResearchPlanningPolicy`/`ResearchPlanner.plan()` actually enforces per
complexity (SIMPLE=1, MODERATE=3, COMPLEX=5) -- a MODERATE plan with 5
tasks read as compliant to the model but was always rejected post-hoc
with `ResearchPlannerError`. These tests pin the system prompt to the
policy's real budgets so the two can't drift apart again.
"""

from __future__ import annotations

from app.ai.runtime.research.planner.models import ResearchComplexity
from app.ai.runtime.research.planner.policies import ResearchPlanningPolicy
from app.ai.runtime.research.planner.prompts import planner_system_prompt, planner_user_prompt


def test_system_prompt_states_the_real_per_complexity_task_budget() -> None:
    policy = ResearchPlanningPolicy()
    prompt = planner_system_prompt()

    for complexity in ResearchComplexity:
        max_tasks = policy.budget_for(complexity).max_tasks
        assert f"{complexity.value} allows at most {max_tasks} task" in prompt


def test_system_prompt_does_not_state_a_flat_task_cap() -> None:
    """The old flat "no more than five tasks" phrasing is what caused the
    mismatch -- assert it's gone rather than just that the new text exists,
    so a future edit can't silently reintroduce it alongside the new line."""

    assert "no more than five tasks" not in planner_system_prompt()


def test_user_prompt_defers_to_the_chosen_complexity_budget() -> None:
    prompt = planner_user_prompt(query="How does RAG work?")

    assert "no more than five tasks" not in prompt
    assert "task budget for the complexity" in prompt
    assert "Request: How does RAG work?" in prompt
