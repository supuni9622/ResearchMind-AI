from __future__ import annotations

from app.ai.guardrails.enums import GuardrailCategory, GuardrailSeverity
from app.ai.guardrails.interfaces import GenerationGuardrailInterface
from app.ai.guardrails.models import GuardrailIssue
from app.ai.guardrails.utils.patterns import PII_PATTERNS, match_any
from app.ai.runtime.generation.models import GenerationResult


class PiiLeakageGuardrail(
    GenerationGuardrailInterface,
):
    """
    Foundation-only PII leakage detection on generated output (PRD §10)
    -- the same regex table as `input/pii_detection.py`, applied to
    `GenerationResult.content` instead of the user's prompt. WARNING
    only, same false-positive-rate caveat as the input-side check.
    """

    @property
    def name(
        self,
    ) -> str:
        return "pii_leakage"

    async def check(
        self,
        result: GenerationResult,
    ) -> list[GuardrailIssue]:

        triggered = match_any(
            result.content,
            PII_PATTERNS,
        )

        if not triggered:
            return []

        return [
            GuardrailIssue(
                code="pii_leaked",
                severity=GuardrailSeverity.WARNING,
                category=GuardrailCategory.PII,
                message=f"Response may leak PII: {triggered}",
                metadata={"pii_types": triggered},
            )
        ]
