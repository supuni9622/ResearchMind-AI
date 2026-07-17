from __future__ import annotations

from app.ai.runtime.generation.validation.models import (
    ValidationResult,
)
from pydantic import (
    BaseModel,
    ConfigDict,
)


class RuntimeValidationPolicy(
    BaseModel,
):
    """
    Decides whether a failed runtime-stage `ValidationResult` (a
    Research/Planner/Reviewer/Agent/MCP contract failure -- see
    `validation/runtime/`) should also gate `GenerationService`'s
    regeneration loop, on top of contributing to `ValidationReport.
    overall_score`/`valid` the way it already does unconditionally.

    Defaults to `False`: today, nothing sets `GenerationRequest.runtime`
    in production (see `validation/runtime/service.py`'s docstring), so
    this is inert until a real Research/Planner/Reviewer/Agent/MCP
    runtime starts issuing requests with `runtime` set -- at which
    point a caller can opt in via `block_on_error=True` without any
    change to `GenerationService` itself.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    block_on_error: bool = False

    def should_block(
        self,
        result: ValidationResult,
    ) -> bool:

        if not self.block_on_error:
            return False

        return not result.valid
