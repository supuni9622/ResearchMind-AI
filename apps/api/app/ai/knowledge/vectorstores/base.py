"""
Base Vector Store provider.

Provides common functionality shared by all vector store providers.

Concrete providers are responsible only for communicating with the
underlying vector database.

The base provider centralizes:

- provider configuration
- configuration fingerprint
- provider version
"""

from __future__ import annotations

import hashlib
from abc import ABC
from typing import Generic, TypeVar

from pydantic import BaseModel

from app.ai.knowledge.vectorstores.interfaces import (
    VectorStoreProviderInterface,
)

ConfigT = TypeVar("ConfigT", bound=BaseModel)


class BaseVectorStoreProvider(
    VectorStoreProviderInterface,
    Generic[ConfigT],
    ABC,
):
    """
    Base class for all vector store providers.

    Responsibilities:

    - provider configuration
    - provider version
    - configuration fingerprint

    Concrete providers are responsible only for implementing vector
    database operations.
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
        Version of the provider implementation.
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

        Used for reproducibility, experimentation and future debugging.
        """

        return self._configuration_fingerprint
