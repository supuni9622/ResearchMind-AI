"""
Voyage AI reranker.
"""

from __future__ import annotations

from time import perf_counter

from voyageai.client import Client as VoyageAIClient

from app.ai.knowledge.reranking.base import (
    BaseRerankingProvider,
)
from app.ai.knowledge.reranking.config import (
    VoyageRerankerConfig,
)
from app.ai.knowledge.reranking.enums import (
    RerankingProvider,
)
from app.ai.knowledge.reranking.models import (
    RerankedChunk,
    RerankingRequest,
    RerankingResult,
)
from app.core.settings import settings


class VoyageReranker(
    BaseRerankingProvider,
):
    """
    Voyage AI reranker.
    """

    def __init__(
        self,
        config: VoyageRerankerConfig,
    ) -> None:
        self._config = config

        self._client = VoyageAIClient(
            api_key=settings.voyage_api_key,
        )

    @property
    def provider(
        self,
    ) -> RerankingProvider:
        return RerankingProvider.VOYAGE_AI

    async def rerank(
        self,
        request: RerankingRequest,
    ) -> RerankingResult:

        started = perf_counter()

        response = self._client.rerank(
            query=request.query,
            documents=[chunk.content for chunk in request.chunks],
            model=self._config.model,
            top_k=request.top_k,
        )

        duration_ms = (perf_counter() - started) * 1000

        chunks = []

        for result in response.results:
            chunk = request.chunks[result.index]

            chunks.append(
                RerankedChunk(
                    chunk=chunk,
                    rerank_score=float(
                        result.relevance_score,
                    ),
                )
            )

        return RerankingResult(
            chunks=chunks,
            duration_ms=duration_ms,
        )
