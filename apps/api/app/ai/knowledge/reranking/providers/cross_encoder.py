from __future__ import annotations

from time import perf_counter

from sentence_transformers import (
    CrossEncoder,
)

from app.ai.knowledge.reranking.base import (
    BaseRerankingProvider,
)
from app.ai.knowledge.reranking.config import (
    CrossEncoderConfig,
)
from app.ai.knowledge.reranking.enums import (
    RerankingProvider,
)
from app.ai.knowledge.reranking.models import (
    RerankedChunk,
    RerankingRequest,
    RerankingResult,
)


class CrossEncoderReranker(
    BaseRerankingProvider,
):
    """
    Local CrossEncoder reranker.
    """

    def __init__(
        self,
        config: (CrossEncoderConfig),
    ):
        self._config = config

        self._model = CrossEncoder(
            config.model,
        )

    @property
    def provider(
        self,
    ) -> RerankingProvider:
        return RerankingProvider.CROSS_ENCODER

    async def rerank(
        self,
        request: (RerankingRequest),
    ) -> RerankingResult:

        started = perf_counter()

        pairs = [
            (
                request.query,
                chunk.content,
            )
            for chunk in request.chunks
        ]

        scores = self._model.predict(
            pairs,
        )

        ranked = sorted(
            zip(
                request.chunks,
                scores,
                strict=True,
            ),
            key=lambda x: x[1],
            reverse=True,
        )

        duration_ms = (perf_counter() - started) * 1000

        return RerankingResult(
            chunks=[
                RerankedChunk(
                    chunk=chunk,
                    rerank_score=float(
                        score,
                    ),
                )
                for chunk, score in ranked[: request.top_k]
            ],
            duration_ms=duration_ms,
        )
