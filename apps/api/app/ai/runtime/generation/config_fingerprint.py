"""
Production config fingerprint (EVALUATION_PLAN.md §5, §16 phase 5).

Ties a live answer back to the config that produced it -- `surface`,
`prompt_version`, `chunking_strategy`, `embedding_model`, `reranker`
thread through `GenerationRequest` -> `GenerationUsage` so a regression
can be sliced by exactly what changed. Distinct from the *retrieval-
experiment* metadata `benchmarks/`/LangSmith experiment tracking owns
(`retriever_version`, `chunk_size`, `fusion_method`, ...) -- that's an
offline concern; this is what ties a specific *production* answer back
to its config, per §5's explicit "two different things, don't conflate
them."

`CURRENT_*` below mirror the *actual* live defaults hardcoded elsewhere
in the codebase, listed per-constant. They are not independently
configurable here -- if one of those defaults changes, this module must
be updated in the same change, or the fingerprint silently goes stale.
Only the answer-producing generation calls (Chat, Linear Research, Deep
Research synthesis) populate a fingerprint; internal helper calls
(planning, review, tool-necessity checks, memory extraction) don't --
`chunking_strategy`/`embedding_model`/`reranker` aren't meaningful for a
call that doesn't retrieve.
"""

from __future__ import annotations

CURRENT_CHUNKING_STRATEGY = "markdown"
"""Mirrors `ChunkingStrategy.MARKDOWN`, hardcoded as the live ingestion
strategy in `app/ai/knowledge/processing/service.py` (other strategies
are commented out there as historical alternatives)."""

CURRENT_EMBEDDING_MODEL = "voyage-3-lite"
"""Mirrors `VoyageAIEmbeddingConfig.model_name`'s default
(`app/ai/knowledge/embeddings/config.py`), the live embedding model for
both indexing and query embedding (`QueryEmbeddingService`'s default
provider is `EmbeddingProvider.VOYAGE_AI`,
`app/ai/knowledge/retrieval/query/dense_service.py`)."""

CURRENT_RERANKER = "voyage_ai"
"""Mirrors `RerankingProvider.VOYAGE_AI`, hardcoded as the live reranker
in `app/ai/knowledge/retrieval/service.py`. Reflects the *configured*
reranker, not whether reranking actually ran for a given request (it's
skipped when `rerank=False` or there are no chunks to rerank)."""


def config_fingerprint_kwargs(
    *,
    surface: str,
    prompt_version: str,
) -> dict[str, str]:
    """
    Kwargs to spread into a `GenerationRequest(...)` call at an answer-
    producing generation site, e.g.:

        GenerationRequest(
            ...,
            **config_fingerprint_kwargs(surface="chat", prompt_version="chat-v1"),
        )

    `prompt_version` is the one fingerprint field this module can't
    supply a shared default for -- it's inherently per-call-site (see
    the existing, informal `metadata={"prompt_version": ...}` convention
    already in use at `synthesis/service.py`, `planner/service.py`,
    `review.py`, `web_search/necessity.py`, `chat/paper_query.py` --
    this makes that convention a first-class, typed field for the
    answer-producing call sites specifically, without touching the
    others).
    """

    return {
        "surface": surface,
        "prompt_version": prompt_version,
        "chunking_strategy": CURRENT_CHUNKING_STRATEGY,
        "embedding_model": CURRENT_EMBEDDING_MODEL,
        "reranker": CURRENT_RERANKER,
    }
