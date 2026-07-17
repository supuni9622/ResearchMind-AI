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

_MIN_STEPS = 1


class PlannerRuntimeContract(
    BaseRuntimeContract,
):
    """
    Planner Runtime Contract — requires a non-empty `plan` field, at
    least one `steps` item, and a well-formed dependency graph between
    steps (every `depends_on` reference resolves to a real step, no
    circular dependency).

    Entirely composed from the generic runtime validators, same as
    `ResearchRuntimeContract`: `CompletenessValidator` covers "plan
    exists"/"steps exist", `DependencyValidator` covers "dependencies
    valid".
    """

    def __init__(
        self,
    ) -> None:
        self._checks: list[OutputValidatorInterface] = [
            CompletenessValidator(
                required_fields=[
                    "plan",
                ],
                list_minimums={
                    "steps": _MIN_STEPS,
                },
            ),
            DependencyValidator(
                list_field="steps",
                dependency_key="depends_on",
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
