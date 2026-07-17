from __future__ import annotations

from app.ai.runtime.generation.validation.models import (
    ValidationResult,
)
from pydantic import (
    BaseModel,
    ConfigDict,
)


class FailFastPolicy(
    BaseModel,
):
    """
    Decides whether an input-stage `ValidationResult` should stop
    generation before the provider is ever called.

    Consumed by `GenerationService._enforce_fail_fast_input_validation`,
    which runs `ValidationService.validate_input()` up front (before
    guardrails, routing, or the provider call) precisely so a request
    that's already known to be invalid never pays for any of that work.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    stop_on_error: bool = True
    """
    Default `True`: any ERROR-severity input issue stops generation
    outright. Set `False` for a caller that wants input issues surfaced
    on `ValidationReport` (still computed later, post-generation) but
    never treated as fatal on their own.
    """

    def should_stop(
        self,
        result: ValidationResult,
    ) -> bool:

        if not self.stop_on_error:
            return False

        return not result.valid
