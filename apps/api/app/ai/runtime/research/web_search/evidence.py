"""Normalizes a `WebSearchResult` into the same `ResearchEvidenceReference`
shape document evidence already uses (web_search_tool_platform_prd.md §21),
after scanning extracted content through the existing Context Guardrails
Platform (reused, not rebuilt -- PRD §15.1) for prompt-injection risk.
"""

from __future__ import annotations

from urllib.parse import urlsplit
from uuid import UUID, uuid4

import structlog

from app.ai.knowledge.context.guardrails.create import create_context_guardrail_service
from app.ai.knowledge.context.guardrails.enums import ChunkRiskLevel, GuardrailStrategy
from app.ai.knowledge.context.models import ContextChunk
from app.ai.runtime.research.retrieval.models import ResearchEvidenceReference
from app.ai.tools.web_search.models import WebSearchResult

logger = structlog.get_logger()

MAX_WEB_EVIDENCE_ITEMS = 8
MAX_EXCERPT_CHARACTERS = 500


def _canonical_url(url: str) -> str:
    split = urlsplit(url)
    path = split.path.rstrip("/") or "/"
    return f"{split.scheme}://{split.netloc}{path}"


async def normalize_web_search_result(
    result: WebSearchResult,
    *,
    owner_id: UUID,
    research_run_id: UUID,
    round_number: int = 1,
) -> list[ResearchEvidenceReference]:
    """Best-effort: a guardrail-service failure drops web evidence for this
    round rather than failing the run (PRD §5.7) -- the existing document
    evidence already gathered is unaffected.

    `round_number` (the run's own `web_search_count` at call time) keeps
    citation markers unique across more than one web-search round in the
    same run -- the default policy caps this at one round, but a higher
    `WEB_SEARCH_MAX_CALLS_PER_RUN` must not let a second round's "W1" collide
    with the first's in `ResearchEvidenceBundle.citation_ids` (a flat set)."""

    items = result.items[:MAX_WEB_EVIDENCE_ITEMS]
    if not items:
        return []

    chunks = [
        ContextChunk(
            chunk_id=uuid4(),
            document_id=uuid4(),
            filename=item.title or item.domain,
            owner_id=str(owner_id),
            chunk_index=index,
            content=(item.raw_content or item.snippet)[:MAX_EXCERPT_CHARACTERS],
            score=item.provider_score if item.provider_score is not None else 0.5,
        )
        for index, item in enumerate(items)
    ]

    try:
        guardrail_result = await create_context_guardrail_service().validate(
            strategy=GuardrailStrategy.RULE_BASED,
            chunks=chunks,
        )
        scanned_chunks = guardrail_result.chunks
    except Exception as exc:
        logger.warning(
            "research_runtime.web_search.guardrail_scan_failed",
            research_run_id=str(research_run_id),
            error_type=type(exc).__name__,
        )
        return []

    references: list[ResearchEvidenceReference] = []
    for index, (item, chunk) in enumerate(zip(items, scanned_chunks, strict=True), start=1):
        if chunk.risk_level is ChunkRiskLevel.MALICIOUS:
            logger.warning(
                "research_runtime.web_search.evidence_rejected",
                research_run_id=str(research_run_id),
                domain=item.domain,
                risk_reasons=chunk.risk_reasons,
            )
            continue
        references.append(
            ResearchEvidenceReference(
                document_id=_canonical_url(item.url),
                chunk_id=f"web:{chunk.chunk_id}",
                filename=item.title or item.domain,
                # Short, single-letter-prefixed marker matching the existing
                # "S1"/"S2" document citation style (PRD §24) -- also keeps
                # `CitationCard`'s `citation_id.slice(1)` display working
                # unchanged, the same way it already does for "S1" -> "1".
                citation_id=f"W{round_number}-{index}",
                score=item.provider_score if item.provider_score is not None else 0.5,
                excerpt=chunk.content,
                source_type="web",
            )
        )
    return references
