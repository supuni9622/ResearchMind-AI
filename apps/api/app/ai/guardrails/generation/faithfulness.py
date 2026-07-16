from __future__ import annotations

from app.ai.guardrails.constants import FAITHFULNESS_THRESHOLD
from app.ai.guardrails.enums import GuardrailCategory, GuardrailSeverity
from app.ai.guardrails.interfaces import GenerationGuardrailInterface
from app.ai.guardrails.models import GuardrailIssue
from app.ai.runtime.generation.models import GenerationResult
from app.ai.runtime.generation.validation.output.hallucination_validator import (
    HallucinationValidator,
)


class FaithfulnessGuardrail(
    GenerationGuardrailInterface,
):
    """
    Groundedness/hallucination gate (PRD §10, P1 -- "Reuse: Validation
    Platform"). Wraps `HallucinationValidator` rather than
    recomputing the lexical-overlap groundedness score.

    Deliberately reinterprets the same score more strictly than
    Validation does: `HallucinationValidator` treats low groundedness as
    advisory (`ValidationSeverity.WARNING`, since Validation only asks
    "did it work?"), while this guardrail treats it as `ERROR` -- the
    Guardrails Platform is answering "should we regenerate?" (PRD
    Principle 1: Guardrails independent from Validation, same signal,
    different question), and `GuardrailService`'s `RegenerationPolicy`
    only acts on `ERROR`-severity `FAITHFULNESS` issues.
    """

    def __init__(
        self,
        hallucination_validator: HallucinationValidator,
    ) -> None:
        self._hallucination_validator = hallucination_validator

    @property
    def name(
        self,
    ) -> str:
        return "faithfulness"

    async def check(
        self,
        result: GenerationResult,
    ) -> list[GuardrailIssue]:

        outcome = await self._hallucination_validator.validate(
            result,
        )

        if outcome.score is None or outcome.score >= FAITHFULNESS_THRESHOLD:
            return []

        return [
            GuardrailIssue(
                code="low_faithfulness",
                severity=GuardrailSeverity.ERROR,
                category=GuardrailCategory.FAITHFULNESS,
                message=(
                    f"Response has low groundedness in the retrieved context "
                    f"(score {outcome.score:.2f}); it may contain unsupported "
                    "or fabricated claims."
                ),
                metadata={
                    "groundedness_score": outcome.score,
                },
            )
        ]
