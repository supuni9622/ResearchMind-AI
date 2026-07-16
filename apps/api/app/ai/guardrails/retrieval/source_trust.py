from __future__ import annotations

from app.ai.guardrails.constants import LOW_TRUST_THRESHOLD
from app.ai.guardrails.enums import GuardrailCategory, GuardrailSeverity
from app.ai.guardrails.interfaces import RetrievalGuardrailInterface
from app.ai.guardrails.models import GuardrailIssue
from app.ai.guardrails.trust.models import SourceType
from app.ai.guardrails.trust.trust_registry import TrustRegistry
from app.ai.knowledge.context.models import ContextChunk


class SourceTrustGuardrail(
    RetrievalGuardrailInterface,
):
    """
    Flags retrieved chunks from low-trust sources (PRD §9, P1).

    `ContextChunk` has no source-type field today, so the source type is
    read from `chunk.metadata["source_type"]` when a caller has set it,
    defaulting to `SourceType.USER_DOCUMENT` otherwise -- ResearchMind
    currently only ingests user-uploaded documents, no web/news
    ingestion pipeline exists yet. This guardrail is report-only: unlike
    `context_sanitization.py`'s reuse of `ChunkRiskLevel`, no new field
    is added to `ContextChunk` itself.
    """

    def __init__(
        self,
        trust_registry: TrustRegistry,
    ) -> None:
        self._trust_registry = trust_registry

    @property
    def name(
        self,
    ) -> str:
        return "source_trust"

    async def check(
        self,
        chunks: list[ContextChunk],
    ) -> list[GuardrailIssue]:

        issues: list[GuardrailIssue] = []

        for chunk in chunks:
            source_type = self._resolve_source_type(chunk)

            trust_score = self._trust_registry.score_for(source_type)

            if trust_score >= LOW_TRUST_THRESHOLD:
                continue

            issues.append(
                GuardrailIssue(
                    code="low_source_trust",
                    severity=GuardrailSeverity.WARNING,
                    category=GuardrailCategory.SOURCE_TRUST,
                    message=(
                        f"Chunk {chunk.chunk_id} is from a low-trust source "
                        f"({source_type.value}, score {trust_score:.2f})."
                    ),
                    metadata={
                        "chunk_id": str(chunk.chunk_id),
                        "source_type": source_type.value,
                        "trust_score": trust_score,
                    },
                )
            )

        return issues

    @staticmethod
    def _resolve_source_type(
        chunk: ContextChunk,
    ) -> SourceType:

        raw = chunk.metadata.get("source_type")

        if isinstance(raw, str):
            try:
                return SourceType(raw)
            except ValueError:
                pass

        return SourceType.USER_DOCUMENT
