from __future__ import annotations

from pydantic import (
    BaseModel,
    ConfigDict,
)


class RegenerationPolicy(
    BaseModel,
):
    """
    Whether a generation-stage failure should trigger `GuardrailAction.
    REGENERATE` instead of just `WARN` (PRD §12). Consumed by
    `GuardrailService`'s generation-stage action derivation.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    regenerate_on_hallucination: bool = True

    regenerate_on_schema_failure: bool = True
