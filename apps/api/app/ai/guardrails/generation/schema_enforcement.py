from __future__ import annotations

from app.ai.guardrails.enums import GuardrailCategory, GuardrailSeverity
from app.ai.guardrails.interfaces import GenerationGuardrailInterface
from app.ai.guardrails.models import GuardrailIssue
from app.ai.runtime.generation.models import GenerationResult
from app.ai.runtime.generation.validation.models import ValidationSeverity
from app.ai.runtime.generation.validation.output.json_validator import JsonValidator
from app.ai.runtime.generation.validation.output.schema_validator import SchemaValidator

_SEVERITY_MAP: dict[ValidationSeverity, GuardrailSeverity] = {
    ValidationSeverity.WARNING: GuardrailSeverity.WARNING,
    ValidationSeverity.ERROR: GuardrailSeverity.ERROR,
}


class SchemaEnforcementGuardrail(
    GenerationGuardrailInterface,
):
    """
    Structured-output enforcement (PRD §10 -- "Use: Structured Outputs /
    Validation Platform"). Wraps `SchemaValidator` (parsed_output vs.
    JSON Schema) and, optionally, `JsonValidator` (raw content
    well-formedness) rather than reimplementing JSON-Schema validation.
    """

    def __init__(
        self,
        schema_validator: SchemaValidator,
        json_validator: JsonValidator | None = None,
    ) -> None:
        self._schema_validator = schema_validator

        self._json_validator = json_validator

    @property
    def name(
        self,
    ) -> str:
        return "schema_enforcement"

    async def check(
        self,
        result: GenerationResult,
    ) -> list[GuardrailIssue]:

        outcomes = [
            await self._schema_validator.validate(
                result,
            )
        ]

        if self._json_validator is not None:
            outcomes.append(
                await self._json_validator.validate(
                    result,
                )
            )

        issues: list[GuardrailIssue] = []

        for outcome in outcomes:
            for validation_issue in outcome.issues:
                issues.append(
                    GuardrailIssue(
                        code="schema_violation",
                        severity=_SEVERITY_MAP[validation_issue.severity],
                        category=GuardrailCategory.SCHEMA,
                        message=validation_issue.message,
                        metadata={
                            "validator": validation_issue.validator,
                            **validation_issue.details,
                        },
                    )
                )

        return issues
