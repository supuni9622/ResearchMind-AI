"""
Metadata filtering benchmark.

Validates owner_id metadata filtering (see
docs/architecture/metadata-filtering.md) against a real Qdrant index and
quantifies its effect on retrieval quality and latency.

Each benchmark document is assigned its own synthetic owner_id,
simulating per-user document isolation. For every benchmark query, a
"filtered" run constrains search to the owner of the query's relevant
document and is compared against an "unfiltered" baseline, across the
same dense, sparse, and hybrid retrieval strategies exercised by
RetrievalBenchmark.

Metrics reported per candidate:

- Recall@5/10/20, Precision@5/10, MRR (benchmarks/retrieval/metrics.py)
- Latency (avg/p95/p99)
- leakage_rate: fraction of retrieved chunks belonging to a different
  owner than the one requested. This is the benchmark's primary
  correctness signal -- it should be exactly 0.0 for every filtered
  candidate, complementing the unit tests in
  tests/unit/ai/knowledge/retrieval/providers/test_qdrant_filters.py by
  exercising the filter against a real index end-to-end.

Queries whose relevant documents span more than one owner are skipped
(a single equality filter cannot select multiple owners at once) and
counted under `summary.skipped_queries`.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

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
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)

# Dedicated Qdrant collection, separate from BENCHMARK_COLLECTION_NAME in
# benchmarks/retrieval/benchmark.py, so per-document owner_ids assigned
# here never collide with the shared "benchmark" owner used there.
BENCHMARK_COLLECTION_NAME = "benchmark_retrieval_filtering"

TOP_K = 20
RECALL_KS = (5, 10, 20)
PRECISION_KS = (5, 10)

QUERY_DATASET_FILENAME = "retrieval_queries.json"

SearchFn = Callable[
    [str, int, dict[str, Any]],
    Awaitable[tuple[list[RetrievedChunk], float]],
]


class MetadataFilteringBenchmark(Benchmark):
    """
    Validates owner_id metadata filtering against a real Qdrant index.
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
        return "MetadataFiltering"

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

        owner_by_document_id = {
            document.document_id: f"benchmark-owner-{index}"
            for index, document in enumerate(documents)
        }
        owner_by_filename = {
            document.filename: owner_by_document_id[document.document_id] for document in documents
        }

        await self._indexer.index(
            documents,
            owner_ids_by_document_id=owner_by_document_id,
        )

        evaluable_queries, skipped_queries = _partition_by_owner_consistency(
            query_dataset.queries,
            owner_by_filename,
        )

        candidates = [
            await self._evaluate(
                name="dense_unfiltered",
                queries=evaluable_queries,
                owner_by_filename=owner_by_filename,
                search=self._search_dense,
                apply_filter=False,
            ),
            await self._evaluate(
                name="dense_filtered",
                queries=evaluable_queries,
                owner_by_filename=owner_by_filename,
                search=self._search_dense,
                apply_filter=True,
            ),
            await self._evaluate(
                name="sparse_unfiltered",
                queries=evaluable_queries,
                owner_by_filename=owner_by_filename,
                search=self._search_sparse,
                apply_filter=False,
            ),
            await self._evaluate(
                name="sparse_filtered",
                queries=evaluable_queries,
                owner_by_filename=owner_by_filename,
                search=self._search_sparse,
                apply_filter=True,
            ),
            await self._evaluate(
                name="hybrid_unfiltered",
                queries=evaluable_queries,
                owner_by_filename=owner_by_filename,
                search=self._search_hybrid,
                apply_filter=False,
            ),
            await self._evaluate(
                name="hybrid_filtered",
                queries=evaluable_queries,
                owner_by_filename=owner_by_filename,
                search=self._search_hybrid,
                apply_filter=True,
            ),
        ]

        return BenchmarkReport(
            benchmark_name=self.name,
            dataset=BenchmarkDataset(
                name=dataset_path.name,
                document_count=len(documents),
            ),
            candidates=candidates,
            summary=_build_summary(
                candidates,
                skipped_queries=len(skipped_queries),
            ),
        )

    async def _search_dense(
        self,
        query_text: str,
        top_k: int,
        filters: dict[str, Any],
    ) -> tuple[list[RetrievedChunk], float]:
        with Timer() as timer:
            query_vector = await self._query_embedding_service.embed(
                query_text,
            )

            result = await self._retrieval_provider.search(
                query=RetrievalQuery(
                    query=query_text,
                    top_k=top_k,
                    filters=filters,
                ),
                query_vector=query_vector,
            )

        return result.chunks, timer.elapsed_milliseconds

    async def _search_sparse(
        self,
        query_text: str,
        top_k: int,
        filters: dict[str, Any],
    ) -> tuple[list[RetrievedChunk], float]:
        with Timer() as timer:
            sparse_query = await self._sparse_query_embedding_service.embed(
                query_text,
            )

            result = await self._retrieval_provider.search_sparse(
                query=RetrievalQuery(
                    query=query_text,
                    top_k=top_k,
                    filters=filters,
                ),
                sparse_query=sparse_query,
            )

        return result.chunks, timer.elapsed_milliseconds

    async def _search_hybrid(
        self,
        query_text: str,
        top_k: int,
        filters: dict[str, Any],
    ) -> tuple[list[RetrievedChunk], float]:
        # Mirrors RetrievalService.search_hybrid: retrieve a larger
        # candidate pool from each retriever (with the same filter
        # applied to both) so RRF has enough overlap to fuse
        # meaningfully, then fuse back down to top_k.
        candidate_query = RetrievalQuery(
            query=query_text,
            top_k=top_k * 2,
            filters=filters,
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

        return fused.chunks, timer.elapsed_milliseconds

    async def _evaluate(
        self,
        *,
        name: str,
        queries: list[RetrievalBenchmarkQuery],
        owner_by_filename: dict[str, str],
        search: SearchFn,
        apply_filter: bool,
    ) -> BenchmarkCandidate:
        """
        Run every evaluable query through a candidate retriever and
        aggregate Recall@K, Precision@K, MRR, latency, and leakage_rate.
        """

        recall_scores: dict[int, list[float]] = {k: [] for k in RECALL_KS}
        precision_scores: dict[int, list[float]] = {k: [] for k in PRECISION_KS}
        reciprocal_ranks: list[float] = []
        latencies_ms: list[float] = []
        leaked_chunks = 0
        total_chunks = 0
        error: str | None = None

        try:
            for query in queries:
                expected_owner = owner_by_filename[query.relevant_documents[0]]
                filters = {"owner_id": expected_owner} if apply_filter else {}

                chunks, latency_ms = await search(
                    query.query,
                    TOP_K,
                    filters,
                )

                retrieved_filenames = [chunk.filename for chunk in chunks]
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

                total_chunks += len(chunks)
                leaked_chunks += sum(1 for chunk in chunks if chunk.owner_id != expected_owner)
        except Exception as exc:  # noqa: BLE001
            # Retrieval candidates call external, rate-limited SDKs
            # (Voyage AI) and local inference (FastEmbed). One candidate
            # failing should not prevent the report from covering the
            # other.
            error = str(exc)

        metrics: dict[str, float | int | str | bool] = {
            "queries_evaluated": len(reciprocal_ranks),
        }

        for k in RECALL_KS:
            metrics[f"recall_at_{k}"] = average(recall_scores[k])

        for k in PRECISION_KS:
            metrics[f"precision_at_{k}"] = average(precision_scores[k])

        metrics["mrr"] = average(reciprocal_ranks)
        metrics["avg_latency_ms"] = round(average(latencies_ms), 2)
        metrics["p95_latency_ms"] = round(percentile(latencies_ms, 0.95), 2)
        metrics["p99_latency_ms"] = round(percentile(latencies_ms, 0.99), 2)
        metrics["leakage_rate"] = round(leaked_chunks / total_chunks, 4) if total_chunks else 0.0

        notes: dict[str, object] = {
            "top_k_evaluated": TOP_K,
            "filtered": apply_filter,
        }

        if error is not None:
            notes["error"] = error

        return BenchmarkCandidate(
            name=name,
            metrics=metrics,
            notes=notes,
        )


def _partition_by_owner_consistency(
    queries: list[RetrievalBenchmarkQuery],
    owner_by_filename: dict[str, str],
) -> tuple[list[RetrievalBenchmarkQuery], list[RetrievalBenchmarkQuery]]:
    """
    Split queries into those whose relevant documents all belong to a
    single owner (evaluable under one equality filter) and those that
    don't (skipped by this benchmark).
    """

    evaluable: list[RetrievalBenchmarkQuery] = []
    skipped: list[RetrievalBenchmarkQuery] = []

    for query in queries:
        owners = {owner_by_filename[filename] for filename in query.relevant_documents}

        if len(owners) == 1:
            evaluable.append(query)
        else:
            skipped.append(query)

    return evaluable, skipped


def _build_summary(
    candidates: list[BenchmarkCandidate],
    *,
    skipped_queries: int,
) -> dict[str, Any]:
    """
    Summarize the unfiltered vs. filtered comparison per strategy, per
    docs/architecture/metadata-filtering.md's "Evaluation Driven
    Development" section.
    """

    by_name = {candidate.name: candidate for candidate in candidates}
    summary: dict[str, Any] = {"skipped_queries": skipped_queries}

    for strategy in ("dense", "sparse", "hybrid"):
        unfiltered = by_name.get(f"{strategy}_unfiltered")
        filtered = by_name.get(f"{strategy}_filtered")

        if unfiltered is None or filtered is None:
            continue

        summary[f"{strategy}_precision_at_5_delta"] = round(
            float(filtered.metrics["precision_at_5"]) - float(unfiltered.metrics["precision_at_5"]),
            4,
        )
        summary[f"{strategy}_latency_overhead_ms"] = round(
            float(filtered.metrics["avg_latency_ms"]) - float(unfiltered.metrics["avg_latency_ms"]),
            2,
        )
        summary[f"{strategy}_leakage_rate"] = filtered.metrics["leakage_rate"]

    return summary
