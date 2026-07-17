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
from app.ai.runtime.generation.validation.runtime.validators.consistency import (
    ConsistencyValidator as _RuntimeConsistencyValidator,
)


class ConsistencyValidator(
    OutputValidatorInterface,
):
    """
    Checks `GenerationResult.parsed_output` for invalid cross-references
    between its `sections` and `evidence` fields (an evidence item
    naming a `section_id` that doesn't exist is a contradiction between
    what the response claims and what it actually contains).

    Delegates to the generic runtime `ConsistencyValidator` with its
    default field names -- the same referential-integrity check a
    runtime contract composes -- rather than duplicating the logic.
    Runs unconditionally in the main output pipeline, independent of
    whether a runtime contract also happens to apply to this request.
    """

    @property
    def name(
        self,
    ) -> str:
        return "consistency"

    async def validate(
        self,
        result: GenerationResult,
    ) -> ValidatorOutcome:

        delegate = _RuntimeConsistencyValidator()

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
