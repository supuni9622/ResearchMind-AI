"""Versioned planner prompt; hidden reasoning is never persisted or streamed."""

from __future__ import annotations

from app.ai.runtime.research.planner.models import ResearchComplexity, ResearchPlan
from app.ai.runtime.research.planner.policies import ResearchPlanningPolicy

PLANNER_PROMPT_VERSION = "research-planner-v2"


def _task_budget_line() -> str:
    """
    Derived from `ResearchPlanningPolicy` rather than hardcoded, so the prompt
    can never drift from the budget `ResearchPlanner.plan()` actually enforces
    post-hoc (see `ResearchPlannerError` there). Without this, a model is
    free to pick MODERATE/COMPLEX and still get rejected for a task count
    that was never disclosed as invalid for that complexity -- previously
    the prompt only said "no more than five tasks" regardless of complexity,
    so a MODERATE plan with 5 tasks looked compliant to the model but always
    violates the (undisclosed) 3-task MODERATE budget.
    """

    policy = ResearchPlanningPolicy()
    return "; ".join(
        f"{complexity.value} allows at most {policy.budget_for(complexity).max_tasks} task"
        f"{'s' if policy.budget_for(complexity).max_tasks != 1 else ''}"
        for complexity in ResearchComplexity
    )


def planner_system_prompt() -> str:
    return f"""You are the ResearchMind research planner. Produce only the requested JSON.
Create a bounded plan for grounded document research. Do not answer the question, invent
sources, cite documents, or include hidden reasoning. Prefer one focused task unless the
request clearly needs comparison, chronology, or multiple independent aspects. Every task
ID must be lowercase, stable, and dependency-safe.

The task count is capped by the complexity you choose, not by a single flat number:
{_task_budget_line()}. A plan that exceeds its own complexity's limit is rejected outright,
so pick the lowest complexity that still covers the request, and never pad `tasks` beyond
what the request actually needs.

Also set `rewritten_goal`: a self-contained restatement of the request that resolves
pronouns, implicit references, or shorthand (e.g. "compare it with X") using any background
memory supplied below, so the goal reads correctly without that memory attached. If no
background memory is supplied or none of it is relevant, set `rewritten_goal` to the
request verbatim."""


def planner_user_prompt(*, query: str, memory_context: str | None = None) -> str:
    memory_block = f"\n\n{memory_context}\n" if memory_context else ""
    return (
        "Plan this research request. Keep it within the supplied schema and within the "
        "task budget for the complexity you choose."
        f"{memory_block}"
        f"\n\nRequest: {query}"
    )


def planner_schema() -> dict:
    return ResearchPlan.model_json_schema()
