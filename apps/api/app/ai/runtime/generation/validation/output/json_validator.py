from __future__ import annotations

import json

from app.ai.runtime.generation.enums import (
    ResponseFormat,
)
from app.ai.runtime.generation.models import (
    GenerationResult,
)
from app.ai.runtime.generation.structured_output.repair import (
    StructuredOutputRepair,
)
from app.ai.runtime.generation.validation.interfaces import (
    OutputValidatorInterface,
)
from app.ai.runtime.generation.validation.models import (
    ValidationIssue,
    ValidationSeverity,
    ValidatorOutcome,
)

_JSON_EXPECTED_FORMATS = (
    ResponseFormat.JSON,
    ResponseFormat.STRUCTURED,
)


class JsonValidator(
    OutputValidatorInterface,
):
    """
    Checks whether `GenerationResult.content` is well-formed JSON,
    independent of `SchemaValidator` (which only checks the *shape* of
    `parsed_output`, after parsing/repair already happened). This
    catches — and scores — how much repair the raw model output needed
    in the first place.

    Only runs when JSON was actually expected (`response_format` is
    JSON/STRUCTURED, or a schema/output_model was requested) — plain
    text responses have no reason to be JSON.
    """

    @property
    def name(
        self,
    ) -> str:
        return "json"

    async def validate(
        self,
        result: GenerationResult,
    ) -> ValidatorOutcome:

        request = result.request

        json_expected = (
            request.response_format in _JSON_EXPECTED_FORMATS or request.output_schema is not None
        )

        if not json_expected:
            return ValidatorOutcome()

        content = result.content

        try:
            json.loads(
                content,
            )

            return ValidatorOutcome(
                score=1.0,
            )
        except (
            ValueError,
            TypeError,
        ):
            pass

        try:
            StructuredOutputRepair.try_parse_json(
                content,
            )

            return ValidatorOutcome(
                issues=[
                    ValidationIssue(
                        validator=self.name,
                        severity=ValidationSeverity.WARNING,
                        message=(
                            "Response content was not valid JSON as-is but became "
                            "parseable after repair (stripped code fences/trailing "
                            "commas/etc). The provider or prompt may need tightening."
                        ),
                    )
                ],
                score=0.5,
            )
        except (
            ValueError,
            TypeError,
        ):
            pass

        return ValidatorOutcome(
            issues=[
                ValidationIssue(
                    validator=self.name,
                    severity=ValidationSeverity.ERROR,
                    message="Response content is not valid JSON, even after repair.",
                )
            ],
            score=0.0,
        )
