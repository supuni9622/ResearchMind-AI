from __future__ import annotations

from app.ai.guardrails.enums import GuardrailCategory, GuardrailSeverity
from app.ai.guardrails.interfaces import RetrievalGuardrailInterface
from app.ai.guardrails.models import GuardrailIssue
from app.ai.knowledge.context.citations.models import Citation
from app.ai.knowledge.context.models import ContextChunk


class CitationIntegrityGuardrail(
    RetrievalGuardrailInterface,
):
    """
    Deterministic existence check: every citation's referenced chunks
    exist in the retrieved set, and every chunk's citation_id resolves
    to a real citation (PRD §9 -- "citation exists, document exists,
    chunk exists").

    This is a *different*, complementary check from Validation
    Platform's `CitationValidator` (`generation/validation/output/
    citation_validator.py`), which flags citation markers *fabricated
    by the model* in generated text. This one runs earlier, over the
    retrieval set itself, before generation happens at all.

    Needs both `chunks` and `citations`, which doesn't fit the shared
    `RetrievalGuardrailInterface.check(chunks)` signature -- `check()`
    is a no-op here; the real logic is in `check_citations()`, which
    `GuardrailService.evaluate_retrieval()` calls directly when
    citations are supplied (see its `check_citations` duck-typed seam).
    """

    @property
    def name(
        self,
    ) -> str:
        return "citation_integrity"

    async def check(
        self,
        chunks: list[ContextChunk],
    ) -> list[GuardrailIssue]:

        return []

    async def check_citations(
        self,
        *,
        chunks: list[ContextChunk],
        citations: list[Citation],
    ) -> list[GuardrailIssue]:

        issues: list[GuardrailIssue] = []

        known_chunk_ids = {chunk.chunk_id for chunk in chunks}

        known_citation_ids = {citation.citation_id for citation in citations}

        for citation in citations:
            for chunk_id in citation.chunk_ids:
                if chunk_id not in known_chunk_ids:
                    issues.append(
                        GuardrailIssue(
                            code="citation_references_unknown_chunk",
                            severity=GuardrailSeverity.ERROR,
                            category=GuardrailCategory.CITATION_INTEGRITY,
                            message=(
                                f"Citation {citation.citation_id} references chunk "
                                f"{chunk_id}, which is not in the retrieved set."
                            ),
                            metadata={
                                "citation_id": citation.citation_id,
                                "chunk_id": str(chunk_id),
                            },
                        )
                    )

        for chunk in chunks:
            if chunk.citation_id and chunk.citation_id not in known_citation_ids:
                issues.append(
                    GuardrailIssue(
                        code="chunk_has_unresolved_citation",
                        severity=GuardrailSeverity.ERROR,
                        category=GuardrailCategory.CITATION_INTEGRITY,
                        message=(
                            f"Chunk {chunk.chunk_id} references citation "
                            f"{chunk.citation_id}, which does not exist."
                        ),
                        metadata={
                            "chunk_id": str(chunk.chunk_id),
                            "citation_id": chunk.citation_id,
                        },
                    )
                )

        return issues
