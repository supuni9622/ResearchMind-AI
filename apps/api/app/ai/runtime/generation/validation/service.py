from __future__ import annotations

import structlog
from app.ai.runtime.generation.models import (
    GenerationResult,
)
from app.ai.runtime.generation.validation.interfaces import (
    OutputValidatorInterface,
)
from app.ai.runtime.generation.validation.models import (
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)

logger = structlog.get_logger()


class ValidationService:
    def __init__(
        self,
        validators: list[OutputValidatorInterface],
    ) -> None:
        self._validators = validators

    @property
    def validator_names(
        self,
    ) -> list[str]:
        return [validator.name for validator in self._validators]

    async def validate(
        self,
        result: GenerationResult,
    ) -> ValidationResult:

        issues: list[ValidationIssue] = []

        for validator in self._validators:
            try:
                issues.extend(
                    await validator.validate(
                        result,
                    )
                )
            except Exception as exc:
                logger.warning(
                    "validation.validator_failed",
                    validator=validator.name,
                    error_type=type(exc).__name__,
                    error=str(exc),
                )

                issues.append(
                    ValidationIssue(
                        validator=validator.name,
                        severity=ValidationSeverity.WARNING,
                        message=f"Validator crashed: {exc}",
                    )
                )

        valid = not any(issue.severity == ValidationSeverity.ERROR for issue in issues)

        return ValidationResult(
            valid=valid,
            issues=issues,
        )
