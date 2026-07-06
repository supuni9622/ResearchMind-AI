"""
Base embedding provider.

Provides common functionality shared by all embedding implementations.

Concrete providers are responsible only for generating embedding vectors.
Construction of canonical Embedding models is delegated to the
EmbeddingFactory.
"""

from __future__ import annotations

import hashlib
from abc import ABC
from typing import Generic, TypeVar

from pydantic import BaseModel

from app.ai.knowledge.embeddings.interfaces import EmbeddingProvider

ConfigT = TypeVar("ConfigT", bound=BaseModel)


class BaseEmbeddingProvider(
    EmbeddingProvider,
    Generic[ConfigT],
    ABC,
):
    """
    Base class for all embedding providers.

    Responsibilities:

    - provider configuration
    - configuration fingerprint
    - provider version

    Concrete providers are responsible only for generating vectors.
    Canonical Embedding construction is delegated to the
    EmbeddingFactory.
    """

    def __init__(
        self,
        config: ConfigT,
    ) -> None:
        self._config = config

        self._configuration_fingerprint = hashlib.sha256(
            self._config.model_dump_json().encode("utf-8")
        ).hexdigest()

    @property
    def version(self) -> str:
        """
        Provider implementation version.
        """

        return "1.0"

    @property
    def config(self) -> ConfigT:
        """
        Provider configuration.
        """

        return self._config

    @property
    def configuration_fingerprint(self) -> str:
        """
        Stable fingerprint representing the provider configuration.
        """

        return self._configuration_fingerprint
