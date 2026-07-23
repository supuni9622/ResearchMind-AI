from __future__ import annotations

from app.ai.runtime.generation.models import (
    GenerationResult,
)
from app.ai.runtime.generation.validation.interfaces import (
    OutputValidatorInterface,
)
from app.ai.runtime.generation.validation.models import (
    ValidationIssue,
    ValidationSeverity,
    ValidatorOutcome,
)
from app.ai.runtime.generation.validation.runtime.fields import (
    get_field,
)


class ConfidenceValidator(
    OutputValidatorInterface,
):
    """
    Checks a runtime output's confidence-style score field (if
    present) is numeric and falls within `[0, 1]` (PRD §14).
    Contributes it as this check's score when valid. Runs only when
    the field is present — whether it's *required* is a
    contract-level concern (PRD §15), not this validator's.

    `field_name` is configurable since contracts name this
    differently (e.g. the Reviewer Runtime Contract's
    `ModelReviewAssessment.quality_score` vs. a generic `confidence`
    field) rather than each writing a bespoke range-check validator.
    """

    def __init__(
        self,
        *,
        field_name: str = "confidence",
    ) -> None:
        self._field_name = field_name

    @property
    def name(
        self,
    ) -> str:
        return "runtime_confidence"

    async def validate(
        self,
        result: GenerationResult,
    ) -> ValidatorOutcome:

        confidence = get_field(
            result.parsed_output,
            self._field_name,
        )

        if confidence is None:
            return ValidatorOutcome()

        if not isinstance(confidence, int | float) or isinstance(confidence, bool):
            return ValidatorOutcome(
                issues=[
                    ValidationIssue(
                        validator=self.name,
                        severity=ValidationSeverity.ERROR,
                        message=f"Runtime output confidence is not numeric: {confidence!r}.",
                    )
                ],
            )

        if not 0.0 <= float(confidence) <= 1.0:
            return ValidatorOutcome(
                issues=[
                    ValidationIssue(
                        validator=self.name,
                        severity=ValidationSeverity.ERROR,
                        message=(
                            f"Runtime output confidence {confidence} is outside the "
                            "valid range [0, 1]."
                        ),
                        details={
                            "confidence": confidence,
                        },
                    )
                ],
            )

        return ValidatorOutcome(
            score=float(confidence),
        )
