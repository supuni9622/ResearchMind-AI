from __future__ import annotations

from abc import ABC, abstractmethod

from app.ai.runtime.generation.models import (
    GenerationRequest,
    GenerationResult,
)
from app.ai.runtime.generation.validation.models import (
    InputValidationContext,
    ValidatorOutcome,
)


class InputValidatorInterface(
    ABC,
):
    """
    A single input validation check, run before generation.

    Receives the `GenerationRequest` plus an `InputValidationContext`
    carrying provider facts (context window, capability flags) the
    request itself doesn't know. Should not raise for validation
    failures — only for programming errors — and should return an
    empty outcome when it has nothing to check (e.g. no context_window
    supplied).
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
        request: GenerationRequest,
        context: InputValidationContext,
    ) -> ValidatorOutcome:
        pass


class OutputValidatorInterface(
    ABC,
):
    """
    A single output (or hallucination-stage) validation check.

    Receives the full `GenerationResult` (content, parsed_output, and the
    originating `request` — schema, output_model, prompt_context) so each
    validator can pull whatever it needs without a bespoke signature.

    Returns a `ValidatorOutcome`; an empty one means the check passed
    with nothing to score. Validators should not raise for validation
    failures — only for programming errors. A validator that has
    nothing to check against (e.g. no schema, no known citations)
    should return an empty outcome rather than erroring.
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
    ) -> ValidatorOutcome:
        pass
