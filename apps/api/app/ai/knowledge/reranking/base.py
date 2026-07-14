"""
Base reranking provider.
"""

from abc import ABC

from app.ai.knowledge.reranking.interfaces import (
    RerankingProviderInterface,
)


class BaseRerankingProvider(
    RerankingProviderInterface,
    ABC,
):
    VERSION = "1.0.0"

    @property
    def version(
        self,
    ) -> str:
        return self.VERSION
