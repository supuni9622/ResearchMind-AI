"""
Reranking benchmark.

Answers a specific engineering question: given the same hybrid (dense +
sparse, RRF-fused) candidate pool, does reranking that pool with a
cross-encoder or Voyage AI improve result quality enough to justify its
extra latency (and, for Voyage, its cost)?

Candidates:

- hybrid_only: the hybrid candidate pool truncated to the final top-k,
  with no reranking. The baseline.
- hybrid_cross_encoder: the same pool, reranked locally via
  sentence-transformers CrossEncoder (BAAI/bge-reranker-base by
  default). Free, but adds local CPU inference latency.
- hybrid_voyage: the same pool, reranked via the Voyage AI rerank API
  (rerank-2 by default). Paid, adds network latency.

All three candidates see the exact same hybrid pool per query (computed
once and reused), so quality differences are attributable to reranking
alone, not to retrieval variance, and the shared retrieval cost is only
paid once instead of once per candidate.

Metrics reported per candidate: Recall@5, MRR, NDCG@5, and latency
(avg/p95/p99). Recall@5 asks "is the relevant document present in the
top 5 at all?" -- a question hybrid retrieval alone can already answer
well. MRR and NDCG@5 are rank-sensitive: they ask "how high does it
rank?", which is precisely what reranking is supposed to improve, so a
reranker that barely moves Recall while lifting MRR/NDCG is behaving
exactly as expected rather than underperforming.

Cost is reported qualitatively via a `cost_model` note (paid API call
vs. free local inference), matching the convention established in
benchmarks/retrieval/benchmark.py -- this benchmark does not fabricate
a dollar figure, since no token-metered pricing engine exists in this
codebase.

If VOYAGE_API_KEY is not configured, `hybrid_voyage` is not registered
in the reranking registry; that candidate is reported with
`queries_evaluated: 0` and a `skipped` note rather than the whole
benchmark run failing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.ai.knowledge.reranking.enums import RerankingProvider
from app.ai.knowledge.reranking.models import RerankingRequest
from app.ai.knowledge.reranking.registry import RerankingRegistry
from app.ai.knowledge.retrieval.fusion.service import RetrievalFusionService
from app.ai.knowledge.retrieval.models import RetrievalQuery, RetrievedChunk
from app.ai.knowledge.retrieval.providers.qdrant import QdrantRetrievalProvider
from app.ai.knowledge.retrieval.query.dense_service import QueryEmbeddingService
from app.ai.knowledge.retrieval.query.sparse_service import (
    SparseQueryEmbeddingService,
)

from benchmarks.common.dataset_loader import DatasetLoader
from benchmarks.common.metrics import average, percentile
from benchmarks.common.timer import Timer
from benchmarks.interfaces.benchmark import Benchmark
from benchmarks.models.report import (
    BenchmarkCandidate,
    BenchmarkDataset,
    BenchmarkReport,
)
from benchmarks.retrieval.dataset import (
    RetrievalBenchmarkQuery,
    load_retrieval_queries,
)
from benchmarks.retrieval.indexer import BenchmarkRetrievalIndexer
from benchmarks.retrieval.metrics import (
    ndcg_at_k,
    recall_at_k,
    reciprocal_rank,
)

# Dedicated Qdrant collection, isolated from the other retrieval
# benchmarks' collections so runs never interfere with each other.
BENCHMARK_COLLECTION_NAME = "benchmark_reranking"

# Hybrid candidate pool size retrieved before (optional) reranking.
POOL_SIZE = 20

# Final result size after truncation / reranking.
FINAL_K = 5

RECALL_K = 5
NDCG_K = 5

QUERY_DATASET_FILENAME = "retrieval_queries.json"

_HYBRID_COST_MODEL = (
    "Voyage AI dense query embedding (paid, per-token) + FastEmbed SPLADE "
    "sparse embedding (local CPU, free); fused in-process via RRF."
)
_CROSS_ENCODER_COST_MODEL = (
    f"{_HYBRID_COST_MODEL} Reranked via BAAI/bge-reranker-base: local CPU "
    "inference, no marginal cost."
)
_VOYAGE_RERANK_COST_MODEL = (
    f"{_HYBRID_COST_MODEL} Reranked via Voyage AI rerank-2: paid, per-token API call."
)

# A single query's precomputed hybrid candidate pool, shared across every
# candidate so retrieval is only paid for once per query.
_Pool = tuple[RetrievalBenchmarkQuery, list[RetrievedChunk], float]


class RerankingBenchmark(Benchmark):
    """
    Compares hybrid retrieval alone against hybrid retrieval followed by
    cross-encoder or Voyage AI reranking.
    """

    def __init__(
        self,
        *,
        dataset_loader: DatasetLoader,
        indexer: BenchmarkRetrievalIndexer,
        retrieval_provider: QdrantRetrievalProvider,
        query_embedding_service: QueryEmbeddingService,
        sparse_query_embedding_service: SparseQueryEmbeddingService,
        fusion_service: RetrievalFusionService,
        reranking_registry: RerankingRegistry,
    ) -> None:
        self._dataset_loader = dataset_loader
        self._indexer = indexer
        self._retrieval_provider = retrieval_provider
        self._query_embedding_service = query_embedding_service
        self._sparse_query_embedding_service = sparse_query_embedding_service
        self._fusion_service = fusion_service
        self._reranking_registry = reranking_registry

    @property
    def name(self) -> str:
        return "Reranking"

    async def run(
        self,
        dataset_path: Path,
    ) -> BenchmarkReport:
        documents = self._dataset_loader.load_documents(
            dataset_path,
        )

        query_dataset = load_retrieval_queries(
            dataset_path / QUERY_DATASET_FILENAME,
        )

        await self._indexer.index(documents)

        pools: list[_Pool] = []

        for query in query_dataset.queries:
            pool_chunks, retrieval_latency_ms = await self._search_hybrid_pool(
                query.query,
                POOL_SIZE,
            )
            pools.append((query, pool_chunks, retrieval_latency_ms))

        candidates = [
            self._evaluate_hybrid_only(pools),
            await self._evaluate_reranked(
                name="hybrid_cross_encoder",
                provider=RerankingProvider.CROSS_ENCODER,
                pools=pools,
                cost_model=_CROSS_ENCODER_COST_MODEL,
            ),
            await self._evaluate_reranked(
                name="hybrid_voyage",
                provider=RerankingProvider.VOYAGE_AI,
                pools=pools,
                cost_model=_VOYAGE_RERANK_COST_MODEL,
            ),
        ]

        return BenchmarkReport(
            benchmark_name=self.name,
            dataset=BenchmarkDataset(
                name=dataset_path.name,
                document_count=len(documents),
            ),
            candidates=candidates,
            summary=_build_summary(candidates),
        )

    async def _search_hybrid_pool(
        self,
        query_text: str,
        pool_size: int,
    ) -> tuple[list[RetrievedChunk], float]:
        # Mirrors RetrievalService.search_hybrid: retrieve a larger
        # candidate pool from each retriever so RRF has enough overlap
        # to fuse meaningfully, then fuse back down to pool_size.
        candidate_query = RetrievalQuery(
            query=query_text,
            top_k=pool_size * 2,
        )

        with Timer() as timer:
            query_vector = await self._query_embedding_service.embed(
                query_text,
            )

            dense_result = await self._retrieval_provider.search(
                query=candidate_query,
                query_vector=query_vector,
            )

            sparse_query = await self._sparse_query_embedding_service.embed(
                query_text,
            )

            sparse_result = await self._retrieval_provider.search_sparse(
                query=candidate_query,
                sparse_query=sparse_query,
            )

            fused = await self._fusion_service.fuse(
                dense=dense_result,
                sparse=sparse_result,
                top_k=pool_size,
            )

        return fused.chunks, timer.elapsed_milliseconds

    def _evaluate_hybrid_only(
        self,
        pools: list[_Pool],
    ) -> BenchmarkCandidate:
        """
        No reranking: just truncate the hybrid pool to the final size.
        """

        recall_scores: list[float] = []
        reciprocal_ranks: list[float] = []
        ndcg_scores: list[float] = []
        latencies_ms: list[float] = []

        for query, pool_chunks, retrieval_latency_ms in pools:
            retrieved_filenames = [chunk.filename for chunk in pool_chunks[:FINAL_K]]
            relevant = set(query.relevant_documents)

            recall_scores.append(recall_at_k(retrieved_filenames, relevant, RECALL_K))
            reciprocal_ranks.append(reciprocal_rank(retrieved_filenames, relevant))
            ndcg_scores.append(ndcg_at_k(retrieved_filenames, relevant, NDCG_K))
            latencies_ms.append(retrieval_latency_ms)

        return _build_candidate(
            name="hybrid_only",
            recall_scores=recall_scores,
            reciprocal_ranks=reciprocal_ranks,
            ndcg_scores=ndcg_scores,
            latencies_ms=latencies_ms,
            cost_model=_HYBRID_COST_MODEL,
            error=None,
        )

    async def _evaluate_reranked(
        self,
        *,
        name: str,
        provider: RerankingProvider,
        pools: list[_Pool],
        cost_model: str,
    ) -> BenchmarkCandidate:
        if not self._reranking_registry.has(provider):
            return BenchmarkCandidate(
                name=name,
                metrics={"queries_evaluated": 0},
                notes={
                    "cost_model": cost_model,
                    "skipped": (
                        f"{provider.value} reranker is not registered (missing credentials/config)."
                    ),
                },
            )

        reranker = self._reranking_registry.get(provider)

        recall_scores: list[float] = []
        reciprocal_ranks: list[float] = []
        ndcg_scores: list[float] = []
        latencies_ms: list[float] = []
        error: str | None = None

        try:
            for query, pool_chunks, retrieval_latency_ms in pools:
                with Timer() as timer:
                    result = await reranker.rerank(
                        RerankingRequest(
                            query=query.query,
                            chunks=pool_chunks,
                            top_k=FINAL_K,
                        ),
                    )

                retrieved_filenames = [
                    reranked_chunk.chunk.filename for reranked_chunk in result.chunks
                ]
                relevant = set(query.relevant_documents)

                recall_scores.append(recall_at_k(retrieved_filenames, relevant, RECALL_K))
                reciprocal_ranks.append(reciprocal_rank(retrieved_filenames, relevant))
                ndcg_scores.append(ndcg_at_k(retrieved_filenames, relevant, NDCG_K))
                latencies_ms.append(retrieval_latency_ms + timer.elapsed_milliseconds)
        except Exception as exc:  # noqa: BLE001
            # A reranker candidate failing (rate limit, model load
            # failure) should not prevent the report from covering the
            # others.
            error = str(exc)

        return _build_candidate(
            name=name,
            recall_scores=recall_scores,
            reciprocal_ranks=reciprocal_ranks,
            ndcg_scores=ndcg_scores,
            latencies_ms=latencies_ms,
            cost_model=cost_model,
            error=error,
        )


def _build_candidate(
    *,
    name: str,
    recall_scores: list[float],
    reciprocal_ranks: list[float],
    ndcg_scores: list[float],
    latencies_ms: list[float],
    cost_model: str,
    error: str | None,
) -> BenchmarkCandidate:
    metrics: dict[str, float | int | str | bool] = {
        "queries_evaluated": len(reciprocal_ranks),
        f"recall_at_{RECALL_K}": average(recall_scores),
        "mrr": average(reciprocal_ranks),
        f"ndcg_at_{NDCG_K}": average(ndcg_scores),
        "avg_latency_ms": round(average(latencies_ms), 2),
        "p95_latency_ms": round(percentile(latencies_ms, 0.95), 2),
        "p99_latency_ms": round(percentile(latencies_ms, 0.99), 2),
    }

    notes: dict[str, object] = {
        "final_k": FINAL_K,
        "pool_size": POOL_SIZE,
        "cost_model": cost_model,
    }

    if error is not None:
        notes["error"] = error

    return BenchmarkCandidate(
        name=name,
        metrics=metrics,
        notes=notes,
    )


def _build_summary(
    candidates: list[BenchmarkCandidate],
) -> dict[str, Any]:
    """
    Summarize each reranker's effect relative to the hybrid_only
    baseline: reranking is expected to lift MRR/NDCG much more than
    Recall, since Recall only asks whether the relevant document made
    the pool at all, while MRR/NDCG are rank-sensitive.
    """

    by_name = {candidate.name: candidate for candidate in candidates}
    baseline = by_name.get("hybrid_only")
    summary: dict[str, Any] = {}

    if baseline is None:
        return summary

    for name in ("hybrid_cross_encoder", "hybrid_voyage"):
        candidate = by_name.get(name)

        if candidate is None or candidate.metrics.get("queries_evaluated", 0) == 0:
            continue

        summary[f"{name}_recall_at_{RECALL_K}_delta"] = round(
            float(candidate.metrics[f"recall_at_{RECALL_K}"])
            - float(baseline.metrics[f"recall_at_{RECALL_K}"]),
            4,
        )
        summary[f"{name}_mrr_delta"] = round(
            float(candidate.metrics["mrr"]) - float(baseline.metrics["mrr"]),
            4,
        )
        summary[f"{name}_ndcg_at_{NDCG_K}_delta"] = round(
            float(candidate.metrics[f"ndcg_at_{NDCG_K}"])
            - float(baseline.metrics[f"ndcg_at_{NDCG_K}"]),
            4,
        )
        summary[f"{name}_latency_overhead_ms"] = round(
            float(candidate.metrics["avg_latency_ms"]) - float(baseline.metrics["avg_latency_ms"]),
            2,
        )

    return summary
