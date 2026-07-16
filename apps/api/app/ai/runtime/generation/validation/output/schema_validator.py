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
    ValidationSeverity,
    ValidatorOutcome,
)
from jsonschema import (
    SchemaError,
    ValidationError,
)
from jsonschema import (
    validate as jsonschema_validate,
)
from pydantic import BaseModel

logger = structlog.get_logger()


class SchemaValidator(
    OutputValidatorInterface,
):
    """
    Validates `GenerationResult.parsed_output` against
    `GenerationResult.request.output_schema` (standard JSON Schema).

    This is independent of `output_model` validation
    (`GenerationService._validate_parsed_output`, which validates against
    a specific Pydantic class) — it applies to any `output_schema`, even
    a raw dict with no corresponding Pydantic model, and re-validates
    even when `output_model` was already used, since native provider
    structured output isn't schema-enforcement-guaranteed on every
    provider (e.g. Ollama JSON mode, the prompt-instruction fallbacks).
    """

    @property
    def name(
        self,
    ) -> str:
        return "schema"

    async def validate(
        self,
        result: GenerationResult,
    ) -> ValidatorOutcome:

        schema = result.request.output_schema

        if schema is None:
            return ValidatorOutcome()

        if result.parsed_output is None:
            return ValidatorOutcome(
                issues=[
                    ValidationIssue(
                        validator=self.name,
                        severity=ValidationSeverity.ERROR,
                        message=(
                            "A response schema was requested but no parsed_output was produced."
                        ),
                    )
                ],
            )

        payload = result.parsed_output

        if isinstance(
            payload,
            BaseModel,
        ):
            payload = payload.model_dump(
                mode="json",
            )

        try:
            jsonschema_validate(
                instance=payload,
                schema=schema,
            )
        except ValidationError as exc:
            return ValidatorOutcome(
                issues=[
                    ValidationIssue(
                        validator=self.name,
                        severity=ValidationSeverity.ERROR,
                        message=exc.message,
                        details={
                            "path": list(
                                exc.absolute_path,
                            ),
                        },
                    )
                ],
            )
        except SchemaError as exc:
            logger.warning(
                "validation.schema.invalid_schema",
                error=str(exc),
            )

            return ValidatorOutcome(
                issues=[
                    ValidationIssue(
                        validator=self.name,
                        severity=ValidationSeverity.WARNING,
                        message=f"output_schema itself is not a valid JSON Schema: {exc.message}",
                    )
                ],
            )

        return ValidatorOutcome()
