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
from app.ai.runtime.generation.validation.runtime.validators.confidence import (
    ConfidenceValidator,
)

_MIN_RECOMMENDATIONS = 1


class ReviewerRuntimeContract(
    BaseRuntimeContract,
):
    """
    Reviewer Runtime Contract — requires a non-empty `critique` field,
    a numeric `confidence` in `[0, 1]`, and at least one
    `recommendations` item.

    Entirely composed from the generic runtime validators, same as
    `ResearchRuntimeContract`: `CompletenessValidator` covers "critique
    exists"/"confidence score exists"/"recommendations exist" (its
    existence check), `ConfidenceValidator` covers the numeric range
    check on top of that.
    """

    def __init__(
        self,
    ) -> None:
        self._checks: list[OutputValidatorInterface] = [
            CompletenessValidator(
                required_fields=[
                    "critique",
                    "confidence",
                ],
                list_minimums={
                    "recommendations": _MIN_RECOMMENDATIONS,
                },
            ),
            ConfidenceValidator(),
        ]

    @property
    def runtime(
        self,
    ) -> RuntimeType:
        return RuntimeType.REVIEWER

    @property
    def contract_name(
        self,
    ) -> str:
        return "reviewer_contract"

    @property
    def checks(
        self,
    ) -> list[OutputValidatorInterface]:
        return list(
            self._checks,
        )
