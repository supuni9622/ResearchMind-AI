from __future__ import annotations

from enum import StrEnum

from app.ai.runtime.generation.validation.models import (
    ValidationReport,
)
from pydantic import (
    BaseModel,
    ConfigDict,
)


class AcceptanceDecision(StrEnum):
    """What `GenerationService` should do with a generated result, given its `ValidationReport`."""

    ACCEPT = "accept"

    REJECT = "reject"

    REGENERATE = "regenerate"


class AcceptancePolicy(
    BaseModel,
):
    """
    Decides Accept/Reject/Regenerate for a completed generation attempt,
    given its `ValidationReport` and whether structured parsing itself
    failed.

    Mirrors the Guardrails Platform's `RegenerationPolicy` (`guardrails/
    policies/regeneration_policy.py`): a plain, stateless config object
    a caller composes rather than a service, since the decision is a
    pure function of its inputs.

    Only the output stage regenerates by default -- an input-stage
    failure describes the request itself, and re-calling the provider
    with the same request (plus a corrective note) wouldn't fix it, so
    `reject_on_input_invalid` defaults to `False`. `GenerationService`
    already fail-fasts on a bad request before the provider is ever
    called (see `FailFastPolicy`), so this default doesn't leave input
    issues unhandled -- it just means this policy isn't the mechanism
    that catches them.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    regenerate_on_output_invalid: bool = True

    reject_on_input_invalid: bool = False

    def decide(
        self,
        *,
        report: ValidationReport | None,
        parsed_output_missing: bool = False,
    ) -> AcceptanceDecision:

        if (
            report is not None
            and not report.input_validation.valid
            and self.reject_on_input_invalid
        ):
            return AcceptanceDecision.REJECT

        if parsed_output_missing:
            return AcceptanceDecision.REGENERATE

        if (
            report is not None
            and not report.output_validation.valid
            and self.regenerate_on_output_invalid
        ):
            return AcceptanceDecision.REGENERATE

        return AcceptanceDecision.ACCEPT
