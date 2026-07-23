"""Canonical, compact planning contracts owned by ResearchMind."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ResearchComplexity(StrEnum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


class ResearchExecutionStrategy(StrEnum):
    FOCUSED = "focused"
    DECOMPOSED = "decomposed"


class ResearchPlanTask(BaseModel):
    """A dependency-safe unit of future retrieval work; no evidence is stored here."""

    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    question: str = Field(min_length=1, max_length=1_000)
    dependencies: list[str] = Field(default_factory=list, max_length=8)
    priority: int = Field(default=1, ge=1, le=5)


class ResearchPlan(BaseModel):
    """Structured planner result persisted as an artifact in a later milestone."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    goal: str = Field(min_length=1, max_length=4_000)
    rewritten_goal: str | None = Field(
        default=None,
        max_length=4_000,
        description=(
            "Memory-aware restatement of `goal` (e.g. resolving 'compare it with X' "
            "using prior-turn context); None when no memory context was available."
        ),
    )
    complexity: ResearchComplexity
    execution_strategy: ResearchExecutionStrategy
    tasks: list[ResearchPlanTask] = Field(min_length=1, max_length=8)
    approval_required: bool = False
    clarification_question: str | None = Field(default=None, max_length=500)
    limitations: list[str] = Field(default_factory=list, max_length=8)

    @property
    def effective_goal(self) -> str:
        """The goal callers should act on -- the rewritten form when one exists."""

        return self.rewritten_goal or self.goal

    @model_validator(mode="after")
    def validate_task_dependencies(self) -> ResearchPlan:
        task_ids = {task.task_id for task in self.tasks}
        if len(task_ids) != len(self.tasks):
            raise ValueError("Plan task IDs must be unique.")
        for task in self.tasks:
            if task.task_id in task.dependencies:
                raise ValueError(f"Plan task '{task.task_id}' cannot depend on itself.")
            missing = set(task.dependencies) - task_ids
            if missing:
                raise ValueError(
                    f"Plan task '{task.task_id}' has unknown dependencies: {sorted(missing)}."
                )
        if self.execution_strategy is ResearchExecutionStrategy.FOCUSED and len(self.tasks) != 1:
            raise ValueError("Focused plans must contain exactly one task.")
        return self
