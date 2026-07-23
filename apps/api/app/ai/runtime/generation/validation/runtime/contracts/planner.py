from __future__ import annotations

from app.ai.runtime.generation.validation.interfaces import (
    OutputValidatorInterface,
)
from app.ai.runtime.generation.validation.runtime.contracts.base import (
    BaseRuntimeContract,
)
from app.ai.runtime.generation.validation.runtime.enums import (
    RuntimeType,
)
from app.ai.runtime.generation.validation.runtime.validators.completeness import (
    CompletenessValidator,
)
from app.ai.runtime.generation.validation.runtime.validators.dependency import (
    DependencyValidator,
)

_MIN_TASKS = 1


class PlannerRuntimeContract(
    BaseRuntimeContract,
):
    """
    Planner Runtime Contract — requires a non-empty `goal` field, at
    least one `tasks` item, and a well-formed dependency graph between
    tasks (every `dependencies` reference resolves to a real task, no
    circular dependency). Field names mirror `ResearchPlan`/
    `ResearchPlanTask` (`app/ai/runtime/research/planner/models.py`),
    the actual `output_model` the planner requests.

    Entirely composed from the generic runtime validators, same as
    `ResearchRuntimeContract`: `CompletenessValidator` covers "goal
    exists"/"tasks exist", `DependencyValidator` covers "dependencies
    valid".
    """

    def __init__(
        self,
    ) -> None:
        self._checks: list[OutputValidatorInterface] = [
            CompletenessValidator(
                required_fields=[
                    "goal",
                ],
                list_minimums={
                    "tasks": _MIN_TASKS,
                },
            ),
            DependencyValidator(
                list_field="tasks",
                id_keys=("task_id",),
                dependency_key="dependencies",
            ),
        ]

    @property
    def runtime(
        self,
    ) -> RuntimeType:
        return RuntimeType.PLANNER

    @property
    def contract_name(
        self,
    ) -> str:
        return "planner_contract"

    @property
    def checks(
        self,
    ) -> list[OutputValidatorInterface]:
        return list(
            self._checks,
        )
