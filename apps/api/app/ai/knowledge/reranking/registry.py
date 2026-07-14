"""
Reranking provider registry.
"""

from app.ai.knowledge.reranking.enums import (
    RerankingProvider,
)
from app.ai.knowledge.reranking.exceptions import (
    RerankingProviderNotFoundError,
)
from app.ai.knowledge.reranking.interfaces import (
    RerankingProviderInterface,
)


class RerankingRegistry:
    """
    Registry of reranking providers.
    """

    def __init__(
        self,
        providers: list[RerankingProviderInterface],
    ):
        self._providers = {provider.provider: provider for provider in providers}

    def get(
        self,
        provider: RerankingProvider,
    ) -> RerankingProviderInterface:

        reranker = self._providers.get(
            provider,
        )

        if reranker is None:
            raise (RerankingProviderNotFoundError(f"Provider '{provider}' is not registered."))

        return reranker

    def has(
        self,
        provider: RerankingProvider,
    ) -> bool:
        """
        Determine whether a provider is registered.
        """

        return provider in self._providers
