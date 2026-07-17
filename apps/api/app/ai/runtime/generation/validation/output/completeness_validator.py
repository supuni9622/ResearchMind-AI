from __future__ import annotations

from app.ai.runtime.generation.models import (
    GenerationResult,
)
from app.ai.runtime.generation.validation.interfaces import (
    OutputValidatorInterface,
)
from app.ai.runtime.generation.validation.models import (
    ValidatorOutcome,
)
from app.ai.runtime.generation.validation.runtime.validators.completeness import (
    CompletenessValidator as _RuntimeCompletenessValidator,
)

_ARRAY_TYPE = "array"


class CompletenessValidator(
    OutputValidatorInterface,
):
    """
    Checks `GenerationResult.parsed_output` for empty sections, missing
    summaries, or missing required fields -- self-configuring from
    `GenerationResult.request.output_schema`'s own `required`/
    `properties` (standard JSON Schema) rather than needing per-caller
    setup, so it applies to any structured request, not just ones going
    through a runtime contract.

    Delegates the actual field-presence/list-minimum logic to the
    generic runtime `CompletenessValidator` (same checks a runtime
    contract composes, see `validation/runtime/validators/
    completeness.py`) instead of re-implementing it -- a required field
    whose schema type is `array` becomes a `list_minimums` entry (must
    have at least one item), every other required field becomes a
    plain presence check.

    Runs only when `output_schema` is present -- an unstructured
    response has no declared shape to be "complete" against.
    """

    @property
    def name(
        self,
    ) -> str:
        return "completeness"

    async def validate(
        self,
        result: GenerationResult,
    ) -> ValidatorOutcome:

        schema = result.request.output_schema

        if not schema:
            return ValidatorOutcome()

        required = schema.get(
            "required",
            [],
        )

        properties = schema.get(
            "properties",
            {},
        )

        list_minimums = {
            field: 1
            for field in required
            if properties.get(
                field,
                {},
            ).get("type")
            == _ARRAY_TYPE
        }

        required_fields = [field for field in required if field not in list_minimums]

        delegate = _RuntimeCompletenessValidator(
            required_fields=required_fields,
            list_minimums=list_minimums,
        )

        outcome = await delegate.validate(
            result,
        )

        return outcome.model_copy(
            update={
                "issues": [
                    issue.model_copy(
                        update={
                            "validator": self.name,
                        },
                    )
                    for issue in outcome.issues
                ],
            },
        )
