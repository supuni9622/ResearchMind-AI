"""
Base Retrieval Provider.

Provides common functionality shared by all retrieval providers.

Concrete providers should inherit from this class rather than
implementing RetrievalProviderInterface directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Final, Generic, TypeVar

from app.ai.knowledge.retrieval.config import (
    BaseRetrievalConfig,
)
from app.ai.knowledge.retrieval.interfaces import (
    RetrievalProviderInterface,
)
from app.ai.knowledge.retrieval.models import (
    RetrievalQuery,
    RetrievalResult,
)
from app.ai.knowledge.retrieval.query.models import (
    SparseQueryEmbedding,
)

ConfigT = TypeVar("ConfigT", bound=BaseRetrievalConfig)


class BaseRetrievalProvider(
    RetrievalProviderInterface,
    Generic[ConfigT],
    ABC,
):
    """
    Base class for retrieval providers.

    Shared responsibilities:

    - provider configuration
    - provider versioning
    - configuration fingerprinting
    """

    VERSION: Final[str] = "1.0.0"

    def __init__(
        self,
        config: ConfigT,
    ) -> None:
        self._config = config

    @property
    def version(self) -> str:
        """
        Provider implementation version.
        """

        return self.VERSION

    @property
    def config(self) -> ConfigT:
        """
        Provider configuration.
        """

        return self._config

    @property
    def configuration_fingerprint(self) -> str:
        """
        Stable fingerprint uniquely identifying
        the provider configuration.

        Useful for:

        - evaluation
        - reproducibility
        - caching
        - experimentation
        """

        return self._config.model_dump_json()

    @abstractmethod
    async def search_sparse(
        self,
        query: RetrievalQuery,
        sparse_query: SparseQueryEmbedding,
    ) -> RetrievalResult:
        raise NotImplementedError

    @abstractmethod
    async def search_metadata(
        self,
        query: RetrievalQuery,
    ) -> RetrievalResult:
        raise NotImplementedError
