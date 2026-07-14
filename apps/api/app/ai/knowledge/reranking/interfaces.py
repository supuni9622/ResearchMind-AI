"""
Reranking provider interfaces.
"""

from abc import ABC, abstractmethod

from app.ai.knowledge.reranking.enums import (
    RerankingProvider,
)
from app.ai.knowledge.reranking.models import (
    RerankingRequest,
    RerankingResult,
)


class RerankingProviderInterface(
    ABC,
):
    """
    Base reranking provider interface.
    """

    @property
    @abstractmethod
    def provider(
        self,
    ) -> RerankingProvider: ...

    @property
    @abstractmethod
    def version(
        self,
    ) -> str: ...

    @abstractmethod
    async def rerank(
        self,
        request: RerankingRequest,
    ) -> RerankingResult: ...
