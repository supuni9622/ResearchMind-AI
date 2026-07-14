"""
Retrieval benchmark.

Benchmarks dense (Voyage AI), sparse (SPLADE), and hybrid (Reciprocal
Rank Fusion of dense + sparse) retrieval against a shared, dedicated
Qdrant collection built from the benchmark corpus, and produces a
canonical BenchmarkReport.

Relevance is judged at document level using a hand-curated query set
(benchmarks/datasets/research-papers/retrieval_queries.json). See that
dataset's `notes` field and benchmarks/datasets/README.md for the
relevance methodology.

Unlike chunking and embeddings, retrieval evaluation inherently requires
a real vector index to query against. The benchmark builds one via
BenchmarkRetrievalIndexer into a collection dedicated to benchmarking,
so runs never touch production data.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path

from app.ai.knowledge.retrieval.fusion.service import RetrievalFusionService
from app.ai.knowledge.retrieval.models import RetrievalQuery
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
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)

# Dedicated Qdrant collection used for retrieval benchmarking. Kept
# separate from settings.qdrant_collection_name so benchmark runs never
# touch production data.
BENCHMARK_COLLECTION_NAME = "benchmark_retrieval"

# Chunks retrieved per query. Large enough to compute Recall@20 in a
# single search call per candidate (see ADR-020).
TOP_K = 20

# ADR-020 required metrics.
RECALL_KS = (5, 10, 20)
PRECISION_KS = (5, 10)

QUERY_DATASET_FILENAME = "retrieval_queries.json"

SearchFn = Callable[[str, int], Awaitable[tuple[list[str], float]]]


class RetrievalBenchmark(Benchmark):
    """
    Engineering benchmark for the Retrieval Platform.
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
    ) -> None:
        self._dataset_loader = dataset_loader
        self._indexer = indexer
        self._retrieval_provider = retrieval_provider
        self._query_embedding_service = query_embedding_service
        self._sparse_query_embedding_service = sparse_query_embedding_service
        self._fusion_service = fusion_service

    @property
    def name(self) -> str:
        return "Retrieval"

    async def run(
        self,
        dataset_path: Path,
    ) -> BenchmarkReport:
        """
        Execute the retrieval benchmark.

        Args:
            dataset_path:
                Root benchmark dataset directory. Must contain both the
                benchmark documents (paper-XXX/processed_document.json)
                and a retrieval_queries.json ground-truth file.

        Returns:
            Canonical benchmark report.
        """

        documents = self._dataset_loader.load_documents(
            dataset_path,
        )

        query_dataset = load_retrieval_queries(
            dataset_path / QUERY_DATASET_FILENAME,
        )

        await self._indexer.index(documents)

        candidates = [
            await self._evaluate(
                name="dense",
                queries=query_dataset.queries,
                search=self._search_dense,
                cost_model="Voyage AI query embedding: paid, per-token API call.",
            ),
            await self._evaluate(
                name="sparse",
                queries=query_dataset.queries,
                search=self._search_sparse,
                cost_model="FastEmbed SPLADE: local CPU inference, no marginal cost.",
            ),
            await self._evaluate(
                name="hybrid",
                queries=query_dataset.queries,
                search=self._search_hybrid,
                cost_model=(
                    "Voyage AI + FastEmbed SPLADE (dense API cost plus local "
                    "sparse inference), fused in-process via RRF."
                ),
            ),
        ]

        return BenchmarkReport(
            benchmark_name=self.name,
            dataset=BenchmarkDataset(
                name=dataset_path.name,
                document_count=len(documents),
            ),
            candidates=candidates,
        )

    async def _search_dense(
        self,
        query_text: str,
        top_k: int,
    ) -> tuple[list[str], float]:
        with Timer() as timer:
            query_vector = await self._query_embedding_service.embed(
                query_text,
            )

            result = await self._retrieval_provider.search(
                query=RetrievalQuery(
                    query=query_text,
                    top_k=top_k,
                ),
                query_vector=query_vector,
            )

        return [chunk.filename for chunk in result.chunks], timer.elapsed_milliseconds

    async def _search_sparse(
        self,
        query_text: str,
        top_k: int,
    ) -> tuple[list[str], float]:
        with Timer() as timer:
            sparse_query = await self._sparse_query_embedding_service.embed(
                query_text,
            )

            result = await self._retrieval_provider.search_sparse(
                query=RetrievalQuery(
                    query=query_text,
                    top_k=top_k,
                ),
                sparse_query=sparse_query,
            )

        return [chunk.filename for chunk in result.chunks], timer.elapsed_milliseconds

    async def _search_hybrid(
        self,
        query_text: str,
        top_k: int,
    ) -> tuple[list[str], float]:
        # Mirrors RetrievalService.search_hybrid: retrieve a larger
        # candidate pool from each retriever so RRF has enough overlap
        # to fuse meaningfully, then fuse back down to top_k.
        candidate_query = RetrievalQuery(
            query=query_text,
            top_k=top_k * 2,
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
                top_k=top_k,
            )

        return [chunk.filename for chunk in fused.chunks], timer.elapsed_milliseconds

    async def _evaluate(
        self,
        *,
        name: str,
        queries: list[RetrievalBenchmarkQuery],
        search: SearchFn,
        cost_model: str,
    ) -> BenchmarkCandidate:
        """
        Run every benchmark query through a candidate retriever and
        aggregate Recall@K, Precision@K, MRR, and latency.
        """

        recall_scores: dict[int, list[float]] = {k: [] for k in RECALL_KS}
        precision_scores: dict[int, list[float]] = {k: [] for k in PRECISION_KS}
        reciprocal_ranks: list[float] = []
        latencies_ms: list[float] = []
        recall_at_10_by_category: dict[str, list[float]] = {}
        error: str | None = None

        try:
            for query in queries:
                retrieved_filenames, latency_ms = await search(
                    query.query,
                    TOP_K,
                )

                relevant = set(query.relevant_documents)

                for k in RECALL_KS:
                    recall_scores[k].append(
                        recall_at_k(retrieved_filenames, relevant, k),
                    )

                for k in PRECISION_KS:
                    precision_scores[k].append(
                        precision_at_k(retrieved_filenames, relevant, k),
                    )

                reciprocal_ranks.append(
                    reciprocal_rank(retrieved_filenames, relevant),
                )

                latencies_ms.append(latency_ms)

                recall_at_10_by_category.setdefault(query.category, []).append(
                    recall_at_k(retrieved_filenames, relevant, 10),
                )
        except Exception as exc:  # noqa: BLE001
            # Retrieval candidates call external, rate-limited SDKs
            # (Voyage AI) and local inference (FastEmbed). One candidate
            # failing should not prevent the report from covering the
            # other.
            error = str(exc)

        queries_evaluated = len(reciprocal_ranks)

        metrics: dict[str, float | int | str | bool] = {
            "queries_evaluated": queries_evaluated,
        }

        for k in RECALL_KS:
            metrics[f"recall_at_{k}"] = average(recall_scores[k])

        for k in PRECISION_KS:
            metrics[f"precision_at_{k}"] = average(precision_scores[k])

        metrics["mrr"] = average(reciprocal_ranks)
        metrics["avg_latency_ms"] = round(average(latencies_ms), 2)
        metrics["p95_latency_ms"] = round(percentile(latencies_ms, 0.95), 2)
        metrics["p99_latency_ms"] = round(percentile(latencies_ms, 0.99), 2)

        notes: dict[str, object] = {
            "top_k_evaluated": TOP_K,
            "cost_model": cost_model,
            "recall_at_10_by_category": {
                category: round(average(scores), 4)
                for category, scores in recall_at_10_by_category.items()
            },
        }

        if error is not None:
            notes["error"] = error

        return BenchmarkCandidate(
            name=name,
            metrics=metrics,
            notes=notes,
        )
