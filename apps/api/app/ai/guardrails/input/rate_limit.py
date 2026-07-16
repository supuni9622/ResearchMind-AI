from __future__ import annotations

from app.ai.guardrails.interfaces import InputGuardrailInterface
from app.ai.guardrails.models import GuardrailIssue
from app.ai.runtime.generation.models import GenerationRequest


class RateLimitGuardrail(
    InputGuardrailInterface,
):
    """
    Foundation only (PRD §8/§21) -- no request-counting state exists
    anywhere in this codebase yet to check against, so this is a pure
    interface seam: it always allows. A real implementation needs a
    per-user/per-tenant request counter (e.g. backed by Redis or the
    application DB), which is out of scope for this platform's MVP.
    """

    @property
    def name(
        self,
    ) -> str:
        return "rate_limit"

    async def check(
        self,
        request: GenerationRequest,
    ) -> list[GuardrailIssue]:

        return []
