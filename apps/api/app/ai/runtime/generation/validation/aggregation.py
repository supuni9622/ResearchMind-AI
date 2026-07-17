from __future__ import annotations

import structlog
from app.ai.runtime.generation.validation.models import (
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
    ValidationStage,
    ValidatorOutcome,
)

logger = structlog.get_logger()


def crash_outcome(
    *,
    validator_name: str,
    stage: ValidationStage,
    exc: Exception,
) -> ValidatorOutcome:
    """Converts a validator crash into a WARNING issue instead of propagating it."""

    logger.warning(
        "validation.validator_failed",
        validator=validator_name,
        stage=stage.value,
        error_type=type(exc).__name__,
        error=str(exc),
    )

    return ValidatorOutcome(
        issues=[
            ValidationIssue(
                validator=validator_name,
                stage=stage,
                severity=ValidationSeverity.WARNING,
                message=f"Validator crashed: {exc}",
            )
        ],
    )


def aggregate_outcomes(
    *,
    stage: ValidationStage,
    outcomes: list[ValidatorOutcome],
) -> ValidationResult:
    """Merges per-validator outcomes into a single stage-level `ValidationResult`."""

    issues: list[ValidationIssue] = []

    scores: list[float] = []

    for outcome in outcomes:
        issues.extend(
            issue.model_copy(
                update={
                    "stage": stage,
                },
            )
            for issue in outcome.issues
        )

        if outcome.score is not None:
            scores.append(
                outcome.score,
            )

    valid = not any(issue.severity == ValidationSeverity.ERROR for issue in issues)

    score = sum(scores) / len(scores) if scores else None

    return ValidationResult(
        valid=valid,
        issues=issues,
        score=score,
    )
