from __future__ import annotations

from pydantic import (
    BaseModel,
    ConfigDict,
)


class RuntimePolicy(
    BaseModel,
):
    """
    Whether a runtime-stage failure (budget/loop) should trigger
    `GuardrailAction.BLOCK` instead of just `WARN` (PRD §12). Consumed by
    `GuardrailService`'s runtime-stage action derivation.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    stop_on_budget_violation: bool = True
