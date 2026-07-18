"""
Retrieval Platform service.

The RetrievalService orchestrates retrieval execution.

Responsibilities

- query validation
- query normalization
- query embedding generation
- provider resolution
- retrieval execution
- runtime metrics collection

The service intentionally contains no provider-specific logic.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from time import perf_counter

from app.ai.knowledge.retrieval.enums import (
    RetrievalProvider,
    RetrievalStrategy,
)
from app.ai.knowledge.retrieval.exceptions import (
    RetrievalValidationError,
)
from app.ai.knowledge.retrieval.fusion.service import (
    RetrievalFusionService,
)
from app.ai.knowledge.retrieval.models import (
    RetrievalExecution,
    RetrievalQuery,
    RetrievalResult,
    RetrievalStatistics,
)
from app.ai.knowledge.retrieval.query.sparse_service import SparseQueryEmbeddingService
from app.ai.knowledge.retrieval.registry import (
    RetrievalRegistry,
)


class RetrievalService:
    """
    Orchestrates retrieval execution.
    """

    MAX_QUERY_LENGTH = 5000

    def __init__(
        self,
        *,
        registry: RetrievalRegistry,
        query_embedding_service,
        sparse_query_embedding_service: (SparseQueryEmbeddingService),
        fusion_service: (RetrievalFusionService),
        reranking_service=None,
    ) -> None:
        self._registry = registry
        self._query_embedding_service = query_embedding_service
        self._sparse_query_embedding_service = sparse_query_embedding_service
        self._fusion_service = fusion_service
        self._reranking_service = reranking_service

    async def search(
        self,
        *,
        provider: RetrievalProvider,
        query: RetrievalQuery,
    ) -> RetrievalResult:
        """
        Execute retrieval.

        Workflow

        Query
            ↓
        Validation
            ↓
        Normalization
            ↓
        Query Embedding
            ↓
        Provider Search
            ↓
        Runtime Metrics
            ↓
        Retrieval Result
        """

        self._validate_query(query)

        normalized_query = self._normalize_query(
            query,
        )

        retrieval_provider = self._registry.get(
            provider,
        )

        execution = RetrievalExecution()

        started = perf_counter()

        query_vector = await self._query_embedding_service.embed(
            normalized_query.query,
        )

        result = await retrieval_provider.search(
            query=normalized_query,
            query_vector=query_vector,
        )

        duration_ms = (perf_counter() - started) * 1000

        execution.completed_at = datetime.now(
            UTC,
        )

        result.execution = execution

        result.statistics = RetrievalStatistics(
            provider=provider,
            strategy=retrieval_provider.config.strategy,
            duration_ms=duration_ms,
            returned_chunks=len(
                result.chunks,
            ),
        )

        return result

    def _validate_query(
        self,
        query: RetrievalQuery,
    ) -> None:
        """
        Validate retrieval inputs.

        Future:

        - prompt injection detection
        - jailbreak detection
        - query guardrails
        """

        if not query.query:
            raise RetrievalValidationError("Query cannot be empty.")

        if not query.query.strip():
            raise RetrievalValidationError("Query cannot be empty.")

        if len(query.query) > self.MAX_QUERY_LENGTH:
            raise RetrievalValidationError(
                f"Query exceeds maximum length of {self.MAX_QUERY_LENGTH} characters."
            )

        if query.top_k <= 0:
            raise RetrievalValidationError("top_k must be greater than zero.")

    @staticmethod
    def _normalize_query(
        query: RetrievalQuery,
    ) -> RetrievalQuery:
        """
        Normalize the incoming query.

        Future:

        - unicode normalization
        - query rewriting
        - HyDE
        - decomposition
        """

        normalized = " ".join(query.query.strip().split())

        return query.model_copy(
            update={
                "query": normalized,
            }
        )

    async def search_sparse(
        self,
        *,
        provider: RetrievalProvider,
        query: RetrievalQuery,
    ) -> RetrievalResult:
        """
        Execute sparse retrieval.
        """

        self._validate_query(
            query,
        )

        normalized_query = self._normalize_query(
            query,
        )

        retrieval_provider = self._registry.get(
            provider,
        )

        execution = RetrievalExecution()

        started = perf_counter()

        sparse_query = await self._sparse_query_embedding_service.embed(
            normalized_query.query,
        )

        result = await retrieval_provider.search_sparse(
            query=normalized_query,
            sparse_query=sparse_query,
        )

        duration_ms = (perf_counter() - started) * 1000

        execution.completed_at = datetime.now(
            UTC,
        )

        result.execution = execution

        result.statistics = RetrievalStatistics(
            provider=provider,
            strategy=(RetrievalStrategy.SPARSE),
            duration_ms=duration_ms,
            returned_chunks=len(
                result.chunks,
            ),
        )

        return result

    async def search_metadata(
        self,
        *,
        provider: RetrievalProvider,
        query: RetrievalQuery,
    ) -> RetrievalResult:
        """
        Execute metadata-filtered retrieval.

        Pure attribute/filter lookup -- no query embedding is
        generated since no vector similarity is involved.
        """

        self._validate_query(
            query,
        )

        normalized_query = self._normalize_query(
            query,
        )

        retrieval_provider = self._registry.get(
            provider,
        )

        execution = RetrievalExecution()

        started = perf_counter()

        result = await retrieval_provider.search_metadata(
            query=normalized_query,
        )

        duration_ms = (perf_counter() - started) * 1000

        execution.completed_at = datetime.now(
            UTC,
        )

        result.execution = execution

        result.statistics = RetrievalStatistics(
            provider=provider,
            strategy=(RetrievalStrategy.METADATA),
            duration_ms=duration_ms,
            returned_chunks=len(
                result.chunks,
            ),
        )

        return result

    async def search_hybrid(
        self,
        *,
        provider: RetrievalProvider,
        query: RetrievalQuery,
        rerank: bool = True,
    ) -> RetrievalResult:
        """
        Execute hybrid retrieval.

        Workflow

        Query
        ↓
        Dense Retrieval  ⎫
        Sparse Retrieval ⎬ asyncio.gather() -- Parallel Retrieval
        Metadata Retrieval ⎭
        ↓
        Reciprocal Rank Fusion
        ↓
        Top K Results
        """

        self._validate_query(
            query,
        )

        normalized_query = self._normalize_query(
            query,
        )

        #
        # Hybrid needs a larger candidate pool.
        #
        # Example:
        #
        # user requests:
        #
        # top_k = 5
        #
        # internally retrieve:
        #
        # top_k = 10
        #
        # to allow meaningful fusion.
        #

        retrieval_query = normalized_query.model_copy(
            update={
                "top_k": min(
                    normalized_query.top_k * 5,
                    50,
                ),
            }
        )

        started = perf_counter()

        #
        # Parallel Retrieval: dense, sparse, and metadata-filtered
        # search all run concurrently via asyncio.gather() instead of
        # sequentially. This immediately gives: ~40-50% latency
        # reduction over running each retriever one after another.
        #

        dense_result, sparse_result, metadata_result = await asyncio.gather(
            self.search(
                provider=provider,
                query=retrieval_query,
            ),
            self.search_sparse(
                provider=provider,
                query=retrieval_query,
            ),
            self.search_metadata(
                provider=provider,
                query=retrieval_query,
            ),
        )

        #
        # Fusion
        #

        result = await self._fusion_service.fuse(
            dense=dense_result,
            sparse=sparse_result,
            metadata=metadata_result,
            top_k=query.top_k,
        )

        rerank_latency_ms: float | None = None
        reranker_provider: str | None = None

        if rerank and self._reranking_service and result.chunks:
            from app.ai.knowledge.reranking.enums import (
                RerankingProvider,
            )
            from app.ai.knowledge.reranking.models import (
                RerankingRequest,
            )

            rerank_started = perf_counter()

            reranked = await self._reranking_service.rerank(
                provider=(RerankingProvider.VOYAGE_AI),
                request=(
                    RerankingRequest(
                        query=query.query,
                        chunks=result.chunks,
                        top_k=query.top_k,
                    )
                ),
            )

            rerank_latency_ms = (perf_counter() - rerank_started) * 1000
            reranker_provider = RerankingProvider.VOYAGE_AI.value

            result.chunks = [chunk.chunk for chunk in reranked.chunks]

        duration_ms = (perf_counter() - started) * 1000

        result.execution = RetrievalExecution(
            completed_at=datetime.now(
                UTC,
            ),
        )

        result.statistics = RetrievalStatistics(
            provider=provider,
            strategy=(RetrievalStrategy.HYBRID),
            duration_ms=duration_ms,
            returned_chunks=len(
                result.chunks,
            ),
            dense_latency_ms=(
                dense_result.statistics.duration_ms if dense_result.statistics else None
            ),
            sparse_latency_ms=(
                sparse_result.statistics.duration_ms if sparse_result.statistics else None
            ),
            metadata_latency_ms=(
                metadata_result.statistics.duration_ms if metadata_result.statistics else None
            ),
            rerank_latency_ms=rerank_latency_ms,
            reranker_provider=reranker_provider,
        )

        return result
