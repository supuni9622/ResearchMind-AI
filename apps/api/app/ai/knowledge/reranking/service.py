"""
Reranking service.
"""

from app.ai.knowledge.reranking.enums import (
    RerankingProvider,
)
from app.ai.knowledge.reranking.exceptions import (
    RerankingValidationError,
)
from app.ai.knowledge.reranking.models import (
    RerankingRequest,
    RerankingResult,
)
from app.ai.knowledge.reranking.registry import (
    RerankingRegistry,
)


class RerankingService:
    """
    Orchestrates reranking execution.
    """

    def __init__(
        self,
        registry: (RerankingRegistry),
    ):
        self._registry = registry

    async def rerank(
        self,
        *,
        provider: (RerankingProvider),
        request: (RerankingRequest),
    ) -> RerankingResult:

        self._validate(
            request,
        )

        reranker = self._registry.get(
            provider,
        )

        return await reranker.rerank(
            request,
        )

    def _validate(
        self,
        request: (RerankingRequest),
    ):

        if not request.query:
            raise (RerankingValidationError("Query cannot be empty."))

        if not request.chunks:
            raise (RerankingValidationError("Chunks cannot be empty."))
