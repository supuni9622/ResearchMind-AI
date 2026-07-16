from __future__ import annotations

from app.ai.guardrails.enums import GuardrailCategory, GuardrailSeverity
from app.ai.guardrails.interfaces import RetrievalGuardrailInterface
from app.ai.guardrails.models import GuardrailIssue
from app.ai.knowledge.context.guardrails.enums import (
    ChunkRiskLevel,
    GuardrailStrategy,
)
from app.ai.knowledge.context.guardrails.service import ContextGuardrailService
from app.ai.knowledge.context.models import ContextChunk

_SEVERITY_BY_RISK_LEVEL: dict[ChunkRiskLevel, GuardrailSeverity] = {
    ChunkRiskLevel.SUSPICIOUS: GuardrailSeverity.WARNING,
    ChunkRiskLevel.MALICIOUS: GuardrailSeverity.ERROR,
}


class ContextSanitizationGuardrail(
    RetrievalGuardrailInterface,
):
    """
    Retrieval-stage prompt-injection detection over retrieved chunks
    (PRD §9, P0 -- "one of the biggest risks").

    This is a pure translation layer over the already-built
    `ContextGuardrailService` (`app.ai.knowledge.context.guardrails`),
    which `ContextChunk.risk_level` is already load-bearing on -- the
    regex detection itself lives there and is not duplicated here.
    """

    def __init__(
        self,
        context_guardrail_service: ContextGuardrailService,
    ) -> None:
        self._context_guardrail_service = context_guardrail_service

    @property
    def name(
        self,
    ) -> str:
        return "context_sanitization"

    async def check(
        self,
        chunks: list[ContextChunk],
    ) -> list[GuardrailIssue]:

        if not chunks:
            return []

        result = await self._context_guardrail_service.validate(
            strategy=GuardrailStrategy.RULE_BASED,
            chunks=chunks,
        )

        issues: list[GuardrailIssue] = []

        for chunk in result.chunks:
            severity = _SEVERITY_BY_RISK_LEVEL.get(chunk.risk_level)

            if severity is None:
                continue

            issues.append(
                GuardrailIssue(
                    code="context_sanitization_flagged",
                    severity=severity,
                    category=GuardrailCategory.PROMPT_INJECTION,
                    message=(
                        f"Chunk {chunk.chunk_id} flagged as {chunk.risk_level.value}: "
                        f"{', '.join(chunk.risk_reasons)}"
                    ),
                    metadata={
                        "chunk_id": str(chunk.chunk_id),
                        "risk_level": chunk.risk_level.value,
                        "risk_reasons": chunk.risk_reasons,
                    },
                )
            )

        return issues
