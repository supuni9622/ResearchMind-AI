"""
Reranking layer contract (EVALUATION_PLAN.md §5, §18 Level 1) -- the last
of §18's six named Level-1 files, previously a 0-byte stub with no Wave 1
item scoped to fill it.

Unlike `test_retrieval_precision.py` (which exercises Recall@K/NDCG@K/
Hit Rate@K/MRR's formulas against real query data -- and `RerankingBenchmark`
reuses those exact same functions, so their correctness is already
covered there), this file checks what's genuinely specific to the
*reranking* layer: `RerankingService.rerank()`'s well-formedness contract
(no provider is centrally forced to preserve the input set or sort its
output -- that's per-provider today, see `service.py`), and whether
reordering by rerank score actually improves ranking quality over the
pre-rerank candidate order on a case a correctly-scoring reranker should
get right. A fake, deterministic `RerankingProviderInterface`
implementation is used throughout -- no live CrossEncoder model load or
Voyage AI call, matching this project's "never verify with live calls"
testing convention for a fast, deterministic unit-test file.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.ai.knowledge.reranking.enums import RerankingProvider
from app.ai.knowledge.reranking.exceptions import RerankingValidationError
from app.ai.knowledge.reranking.models import RerankedChunk, RerankingRequest, RerankingResult
from app.ai.knowledge.reranking.registry import RerankingRegistry
from app.ai.knowledge.reranking.service import RerankingService
from app.ai.knowledge.retrieval.models import RetrievedChunk

from benchmarks.retrieval.metrics import ndcg_at_k, reciprocal_rank


def _chunk(filename: str, *, score: float) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid4(),
        document_id=uuid4(),
        filename=filename,
        owner_id="owner",
        chunk_index=0,
        content=f"content of {filename}",
        score=score,
    )


class _FakeReranker:
    """Deterministic fake satisfying `RerankingProviderInterface` --
    scores each chunk by a hand-assigned relevance map, so the "did
    reranking actually help" test below has a known-correct answer to
    check against, without a live model call."""

    def __init__(self, relevance: dict[str, float]) -> None:
        self._relevance = relevance
        self.provider = RerankingProvider.CROSS_ENCODER
        self.version = "test-fake"

    async def rerank(self, request: RerankingRequest) -> RerankingResult:
        scored = [
            RerankedChunk(chunk=chunk, rerank_score=self._relevance.get(chunk.filename, 0.0))
            for chunk in request.chunks
        ]
        scored.sort(key=lambda entry: entry.rerank_score, reverse=True)
        return RerankingResult(chunks=scored[: request.top_k], duration_ms=1.0)


def _make_service(relevance: dict[str, float]) -> RerankingService:
    reranker = _FakeReranker(relevance)
    registry = RerankingRegistry(providers=[reranker])  # type: ignore[list-item]
    return RerankingService(registry=registry)


@pytest.mark.asyncio
async def test_reranked_output_preserves_the_input_chunk_set() -> None:
    """No provider is centrally forced to avoid dropping/duplicating
    input chunks (see service.py's own module docstring) -- a provider
    that scores every candidate and keeps top_k must still return a
    genuine subset of what it was given, not synthesize or lose items."""

    chunks = [_chunk(f"doc-{i}.pdf", score=0.5) for i in range(5)]
    relevance = {chunk.filename: float(i) for i, chunk in enumerate(chunks)}
    service = _make_service(relevance)

    result = await service.rerank(
        provider=RerankingProvider.CROSS_ENCODER,
        request=RerankingRequest(query="q", chunks=chunks, top_k=5),
    )

    result_filenames = {entry.chunk.filename for entry in result.chunks}
    assert result_filenames == {chunk.filename for chunk in chunks}


async def test_reranked_output_is_sorted_by_score_descending() -> None:
    chunks = [_chunk("a.pdf", score=0.1), _chunk("b.pdf", score=0.1), _chunk("c.pdf", score=0.1)]
    relevance = {"a.pdf": 0.2, "b.pdf": 0.9, "c.pdf": 0.5}
    service = _make_service(relevance)

    result = await service.rerank(
        provider=RerankingProvider.CROSS_ENCODER,
        request=RerankingRequest(query="q", chunks=chunks, top_k=3),
    )

    scores = [entry.rerank_score for entry in result.chunks]
    assert scores == sorted(scores, reverse=True)
    assert [entry.chunk.filename for entry in result.chunks] == ["b.pdf", "c.pdf", "a.pdf"]


async def test_top_k_bounds_the_result_length() -> None:
    chunks = [_chunk(f"doc-{i}.pdf", score=0.5) for i in range(10)]
    relevance = {chunk.filename: 1.0 for chunk in chunks}
    service = _make_service(relevance)

    result = await service.rerank(
        provider=RerankingProvider.CROSS_ENCODER,
        request=RerankingRequest(query="q", chunks=chunks, top_k=3),
    )

    assert len(result.chunks) == 3


async def test_reranking_improves_ndcg_over_a_misordered_candidate_pool() -> None:
    """The actual value proposition of reranking, checked deterministically:
    given a candidate pool where the initial (pre-rerank) retrieval order
    buries the relevant document, a reranker that correctly identifies it
    must produce a *better* NDCG@K than the pre-rerank order -- this is
    what §5's Recall@5/MRR/NDCG@5 reranking-vs-baseline comparison
    (README's benchmark suite section 6) is checking for real, exercised
    here with a known-correct answer instead of a live paid call."""

    relevant_doc = "the-actually-relevant-paper.pdf"
    chunks = [
        _chunk("distractor-1.pdf", score=0.9),
        _chunk("distractor-2.pdf", score=0.85),
        _chunk(relevant_doc, score=0.2),  # buried last by the initial retrieval score
    ]
    pre_rerank_order = [chunk.filename for chunk in chunks]

    # A correctly-scoring reranker ranks the truly relevant document first.
    service = _make_service({relevant_doc: 1.0})

    result = await service.rerank(
        provider=RerankingProvider.CROSS_ENCODER,
        request=RerankingRequest(query="q", chunks=chunks, top_k=3),
    )
    post_rerank_order = [entry.chunk.filename for entry in result.chunks]

    relevant_set = {relevant_doc}
    pre_ndcg = ndcg_at_k(pre_rerank_order, relevant_set, 3)
    post_ndcg = ndcg_at_k(post_rerank_order, relevant_set, 3)

    assert post_ndcg > pre_ndcg
    assert reciprocal_rank(post_rerank_order, relevant_set) == pytest.approx(1.0)


async def test_empty_query_is_rejected_before_any_provider_call() -> None:
    service = _make_service({})

    with pytest.raises(RerankingValidationError):
        await service.rerank(
            provider=RerankingProvider.CROSS_ENCODER,
            request=RerankingRequest(query="", chunks=[_chunk("a.pdf", score=0.5)]),
        )
