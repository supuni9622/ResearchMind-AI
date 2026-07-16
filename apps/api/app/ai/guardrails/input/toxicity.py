from __future__ import annotations

from app.ai.guardrails.interfaces import InputGuardrailInterface
from app.ai.guardrails.models import GuardrailIssue
from app.ai.runtime.generation.models import GenerationRequest


class ToxicityGuardrail(
    InputGuardrailInterface,
):
    """
    Foundation only (PRD §21 explicitly skips Llama Guard/advanced
    moderation for MVP) -- always allows. The seam exists so a future
    classifier-backed provider (Llama Guard or similar) can be dropped
    in without changing `GuardrailRegistry`/`GuardrailService`.
    """

    @property
    def name(
        self,
    ) -> str:
        return "toxicity"

    async def check(
        self,
        request: GenerationRequest,
    ) -> list[GuardrailIssue]:

        return []
