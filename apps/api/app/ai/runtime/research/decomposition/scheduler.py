"""Deterministic, dependency-aware task wave calculation without side effects."""

from __future__ import annotations

from app.ai.runtime.research.decomposition.validators import validate_plan
from app.ai.runtime.research.planner.models import ResearchPlan, ResearchPlanTask


def dependency_waves(plan: ResearchPlan) -> list[list[ResearchPlanTask]]:
    """Return topological waves, ordered stably for reproducible graph fan-out.

    A task starts only after all dependencies are in earlier waves. Ordering within
    a wave is by priority then task ID; it does not impose serial execution.
    """

    validate_plan(plan)
    by_id = {task.task_id: task for task in plan.tasks}
    remaining = set(by_id)
    completed: set[str] = set()
    waves: list[list[ResearchPlanTask]] = []

    while remaining:
        ready = [
            by_id[task_id]
            for task_id in remaining
            if set(by_id[task_id].dependencies).issubset(completed)
        ]
        if not ready:  # ``validate_plan`` already rejects this; defensive only.
            raise RuntimeError("Validated plan had no schedulable tasks.")
        ready.sort(key=lambda task: (task.priority, task.task_id))
        waves.append(ready)
        completed.update(task.task_id for task in ready)
        remaining.difference_update(task.task_id for task in ready)

    return waves
