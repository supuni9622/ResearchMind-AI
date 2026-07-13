"""
Retrieval provider interfaces.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.ai.knowledge.retrieval.config import (
    BaseRetrievalConfig,
)
from app.ai.knowledge.retrieval.enums import (
    RetrievalProvider,
)
from app.ai.knowledge.retrieval.models import (
    RetrievalQuery,
    RetrievalResult,
)
from app.ai.knowledge.retrieval.query.models import (
    SparseQueryEmbedding,
)


class RetrievalProviderInterface(ABC):
    """
    Base retrieval provider interface.
    """

    @property
    @abstractmethod
    def provider(self) -> RetrievalProvider:
        """
        Provider identifier.
        """

    @property
    @abstractmethod
    def version(self) -> str:
        """
        Provider implementation version.
        """

    @property
    @abstractmethod
    def config(self) -> BaseRetrievalConfig:
        """
        Provider configuration.
        """

    @property
    def configuration_fingerprint(self) -> str:
        return self.config.model_dump_json()

    @abstractmethod
    async def search(
        self,
        query: RetrievalQuery,
        query_vector: list[float],
    ) -> RetrievalResult:
        """
        Execute retrieval.
        """

    @abstractmethod
    async def search_sparse(
        self,
        query: RetrievalQuery,
        sparse_query: SparseQueryEmbedding,
    ) -> RetrievalResult:
        """
        Execute sparse retrieval.

        Uses sparse neural vectors
        (FastEmbed SPLADE).

        Future:
            This becomes one branch
            of Hybrid Retrieval.
        """
        raise NotImplementedError
