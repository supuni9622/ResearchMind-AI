from __future__ import annotations

from abc import ABC, abstractmethod

from app.ai.runtime.generation.models import (
    GenerationResult,
)
from app.ai.runtime.generation.validation.models import (
    ValidationIssue,
)


class OutputValidatorInterface(
    ABC,
):
    """
    A single output validation check.

    Receives the full `GenerationResult` (content, parsed_output, and the
    originating `request` — schema, output_model, prompt_context) so each
    validator can pull whatever it needs without a bespoke signature.

    Returns issues found; an empty list means the check passed. Validators
    should not raise for validation failures — only for programming errors.
    A validator that has nothing to check against (e.g. no schema, no
    known citations) should return an empty list rather than erroring.
    """

    @property
    @abstractmethod
    def name(
        self,
    ) -> str:
        pass

    @abstractmethod
    async def validate(
        self,
        result: GenerationResult,
    ) -> list[ValidationIssue]:
        pass
