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


class ReviewerRuntimeContract(
    BaseRuntimeContract,
):
    """
    Reviewer Runtime Contract — requires a numeric `quality_score` in
    `[0, 1]`. Field name mirrors `ModelReviewAssessment`
    (`app/ai/runtime/research/review.py`), the actual `output_model`
    the reviewer step requests: its other fields, `gap_questions` and
    `concerns`, are legitimately optional (an empty list means "no
    concerns found", not a malformed output), so unlike the original
    PRD §15 sketch there's no minimum-count check to make here.

    `CompletenessValidator` covers "quality_score exists",
    `ConfidenceValidator` covers the numeric range check on top of
    that.
    """

    def __init__(
        self,
    ) -> None:
        self._checks: list[OutputValidatorInterface] = [
            CompletenessValidator(
                required_fields=[
                    "quality_score",
                ],
            ),
            ConfidenceValidator(
                field_name="quality_score",
            ),
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
