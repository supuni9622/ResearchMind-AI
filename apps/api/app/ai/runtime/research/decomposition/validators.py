"""Fail-fast validation for the planner's bounded execution DAG."""

from __future__ import annotations

from app.ai.runtime.research.planner.models import ResearchPlan
from app.ai.runtime.research.planner.policies import ResearchPlanningPolicy


class ResearchPlanValidationError(ValueError):
    """A plan defect that must prevent retrieval from starting."""


def validate_plan(
    plan: ResearchPlan,
    *,
    policy: ResearchPlanningPolicy | None = None,
) -> None:
    """Validate the full DAG rather than trusting a structured-model response."""

    policy = policy or ResearchPlanningPolicy()
    budget = policy.budget_for(plan.complexity)
    if len(plan.tasks) > budget.max_tasks:
        raise ResearchPlanValidationError(
            f"Plan has {len(plan.tasks)} tasks, exceeding its {budget.max_tasks}-task budget."
        )

    dependencies = {task.task_id: set(task.dependencies) for task in plan.tasks}
    remaining = set(dependencies)
    while remaining:
        ready = {task_id for task_id in remaining if not dependencies[task_id] & remaining}
        if not ready:
            raise ResearchPlanValidationError("Plan task dependencies contain a cycle.")
        remaining -= ready
