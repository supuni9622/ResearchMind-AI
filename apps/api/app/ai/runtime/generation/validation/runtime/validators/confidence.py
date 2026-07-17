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
    Checks a runtime output's `confidence` (if present) is numeric and
    falls within `[0, 1]` (PRD §14). Contributes it as this check's
    score when valid. Runs only when `confidence` is present — whether
    it's *required* is a contract-level concern (PRD §15), not this
    validator's.
    """

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
            "confidence",
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
