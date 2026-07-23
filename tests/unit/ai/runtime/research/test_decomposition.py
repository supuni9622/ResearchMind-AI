from __future__ import annotations

import pytest
from app.ai.runtime.research.decomposition.scheduler import dependency_waves
from app.ai.runtime.research.decomposition.validators import (
    ResearchPlanValidationError,
    validate_plan,
)
from app.ai.runtime.research.planner.models import (
    ResearchComplexity,
    ResearchExecutionStrategy,
    ResearchPlan,
    ResearchPlanTask,
)


def _plan(*tasks: ResearchPlanTask) -> ResearchPlan:
    return ResearchPlan(
        goal="Compare retrieval approaches",
        complexity=ResearchComplexity.COMPLEX,
        execution_strategy=ResearchExecutionStrategy.DECOMPOSED,
        tasks=list(tasks),
    )


def test_dependency_waves_are_topological_and_stable() -> None:
    plan = _plan(
        ResearchPlanTask(task_id="synthesis-input", question="combine", dependencies=["quality"]),
        ResearchPlanTask(task_id="quality", question="quality", dependencies=["baseline"]),
        ResearchPlanTask(task_id="baseline", question="baseline", priority=2),
        ResearchPlanTask(task_id="cost", question="cost", priority=1),
    )

    assert [[task.task_id for task in wave] for wave in dependency_waves(plan)] == [
        ["cost", "baseline"],
        ["quality"],
        ["synthesis-input"],
    ]


def test_cycle_is_rejected_before_retrieval() -> None:
    plan = _plan(
        ResearchPlanTask(task_id="one", question="one", dependencies=["two"]),
        ResearchPlanTask(task_id="two", question="two", dependencies=["one"]),
    )

    with pytest.raises(ResearchPlanValidationError, match="cycle"):
        validate_plan(plan)
