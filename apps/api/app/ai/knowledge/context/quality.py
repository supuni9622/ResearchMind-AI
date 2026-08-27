"""
Context-construction evaluation (EVALUATION_PLAN.md §6, MVP slice).

A new layer that didn't previously exist as a distinct check: retrieval
can succeed while a later fusion/rerank/compression step silently drops
the evidence that mattered, or context construction can pad the prompt
with more formatting than actual evidence -- nothing previously caught
either failure mode independently of retrieval or generation.

- Provenance preservation reuses `check_citation_validity()`'s
  retrieval-provenance check (`citations/validity.py`, generalized from
  `review_draft()` for EVALUATION_PLAN.md §8) rather than reimplementing
  it, exactly as §6 specifies -- here it's run against *every* citation a
  `PromptContext` carries, not just the ones a generated response ends up
  using, since this check is about whether construction preserved
  evidence, independent of what the model later chose to cite.
- Context token efficiency is a new, deterministic ratio: how much of
  the final formatted context is actual evidence content versus
  formatting/structure overhead.
"""

from __future__ import annotations

from app.ai.knowledge.context.citations.validity import (
    CitationCheckName,
    check_citation_validity,
)
from app.ai.knowledge.context.models import PromptContext
from pydantic import BaseModel, ConfigDict, Field

_APPROXIMATE_TOKENS_PER_WORD = 1.3
"""
Matches `TokenCounter._count_approximate()`'s existing fallback estimate
(`generation/observability/token_counter.py`) -- reused here rather than
introducing a second heuristic, and appropriate for this check
specifically: token efficiency needs a cheap, deterministic, provider-
independent ratio, not per-provider tokenizer accuracy (the real
`TokenCounter` requires live API calls for some providers, which would
make this check non-deterministic and network-dependent).
"""


class ContextConstructionReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provenance_preserved: bool
    """
    True if every citation's claimed chunks are still present in the
    final `PromptContext.chunks` -- false means a construction step
    (fusion, reranking, compression) dropped evidence a citation still
    references, a failure mode retrieval-only or generation-only checks
    cannot see.
    """

    unprovenanced_citation_ids: list[str] = Field(default_factory=list)

    context_token_count: int = Field(ge=0)

    evidence_token_count: int = Field(ge=0)

    token_efficiency: float = Field(ge=0)
    """
    `evidence_token_count / context_token_count`. Not capped to [0, 1]:
    evidence content is usually a *subset* of the formatted context (the
    context also carries headers, citation markup, instructions), so the
    ratio is normally < 1 -- but a custom formatter could in principle
    include chunk content verbatim with near-zero overhead, so this
    isn't artificially bounded.
    """


def _approximate_token_count(
    text: str,
) -> int:

    words = len(text.split())

    return max(1, int(words * _APPROXIMATE_TOKENS_PER_WORD)) if words else 0


def check_context_construction(
    *,
    prompt_context: PromptContext,
) -> ContextConstructionReport:
    """
    Run both context-construction checks against a single `PromptContext`
    -- the same object `check_prompt_context_citation_validity` (§8)
    checks, so this is naturally run alongside it in the same post-hoc
    pass over a response (EVALUATION_PLAN.md §6's own reasoning for why
    provenance preservation reuses §8's logic rather than duplicating it).
    """

    known_citation_ids = {citation.citation_id for citation in prompt_context.citations}

    citation_chunk_ids: dict[str, set[str]] = {
        citation.citation_id: {str(chunk_id) for chunk_id in citation.chunk_ids}
        for citation in prompt_context.citations
    }

    retrieved_chunk_ids = {str(chunk.chunk_id) for chunk in prompt_context.chunks}

    # Every known citation is treated as "used" here -- unlike §8's
    # generation-time check (which only cares about citations the model
    # actually cited), this check asks whether construction preserved
    # *all* available evidence, regardless of what a later generation
    # step chooses to reference.
    validity_report = check_citation_validity(
        used_citation_ids=known_citation_ids,
        known_citation_ids=known_citation_ids,
        citation_chunk_ids=citation_chunk_ids,
        retrieved_chunk_ids=retrieved_chunk_ids,
    )

    provenance_check = next(
        (
            check
            for check in validity_report.checks
            if check.check == CitationCheckName.RETRIEVAL_PROVENANCE
        ),
        None,
    )

    context_tokens = _approximate_token_count(prompt_context.context)

    evidence_tokens = sum(
        _approximate_token_count(chunk.content) for chunk in prompt_context.chunks
    )

    token_efficiency = (evidence_tokens / context_tokens) if context_tokens else 0.0

    return ContextConstructionReport(
        provenance_preserved=provenance_check.passed if provenance_check else True,
        unprovenanced_citation_ids=validity_report.unprovenanced_citation_ids,
        context_token_count=context_tokens,
        evidence_token_count=evidence_tokens,
        token_efficiency=round(token_efficiency, 4),
    )


__all__ = [
    "ContextConstructionReport",
    "check_context_construction",
]
