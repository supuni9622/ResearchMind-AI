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

from datetime import UTC, datetime
from time import perf_counter

from app.ai.knowledge.retrieval.enums import (
    RetrievalProvider,
)
from app.ai.knowledge.retrieval.exceptions import (
    RetrievalValidationError,
)
from app.ai.knowledge.retrieval.models import (
    RetrievalExecution,
    RetrievalQuery,
    RetrievalResult,
    RetrievalStatistics,
)
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
    ) -> None:
        self._registry = registry
        self._query_embedding_service = query_embedding_service

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
