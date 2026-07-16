from __future__ import annotations

from app.ai.guardrails.enums import GuardrailCategory, GuardrailSeverity
from app.ai.guardrails.interfaces import InputGuardrailInterface
from app.ai.guardrails.models import GuardrailIssue
from app.ai.guardrails.utils.patterns import PII_PATTERNS, match_any
from app.ai.runtime.generation.models import GenerationRequest


class PiiDetectionGuardrail(
    InputGuardrailInterface,
):
    """
    Foundation-only PII detection on the user's direct input (PRD §8):
    email, credit-card-shaped, and API-key/token-shaped patterns. Never
    blocks -- WARNING only, since this is regex-shaped detection with a
    real false-positive rate (e.g. any long random-looking string
    matches `generic_token`). Enterprise-grade PII detection is
    explicitly deferred (PRD §21).
    """

    @property
    def name(
        self,
    ) -> str:
        return "pii_detection"

    async def check(
        self,
        request: GenerationRequest,
    ) -> list[GuardrailIssue]:

        triggered = match_any(
            request.user_prompt,
            PII_PATTERNS,
        )

        if not triggered:
            return []

        return [
            GuardrailIssue(
                code="pii_detected",
                severity=GuardrailSeverity.WARNING,
                category=GuardrailCategory.PII,
                message=f"Input may contain PII: {triggered}",
                metadata={"pii_types": triggered},
            )
        ]
