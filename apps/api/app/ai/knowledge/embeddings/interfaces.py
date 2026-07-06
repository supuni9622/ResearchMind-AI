"""
Embedding provider interfaces.

Every embedding implementation must implement the EmbeddingProvider
interface.

The EmbeddingService depends only on this interface, allowing embedding
providers to be replaced without changing application code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel

from app.ai.knowledge.chunking.artifacts.models import ChunkArtifact
from app.ai.knowledge.embeddings.enums import EmbeddingProvider as EmbeddingProviderEnum
from app.ai.knowledge.embeddings.models import Embedding


class EmbeddingProvider(ABC):
    """
    Base interface for every embedding provider.
    """

    @property
    @abstractmethod
    def provider(self) -> EmbeddingProviderEnum:
        """
        Provider identifier.
        """

    @property
    @abstractmethod
    def model(self) -> str:
        """
        Embedding model name.
        """

    @property
    @abstractmethod
    def version(self) -> str:
        """
        Version of the provider implementation.

        Used for experiment tracking and reproducibility.
        """

    @property
    @abstractmethod
    def config(self) -> BaseModel:
        """
        Provider configuration.
        """

    @property
    def configuration_fingerprint(self) -> str:
        """
        Fingerprint uniquely identifying the provider configuration.

        Stored on every generated embedding to support reproducibility.
        """

        return self.config.model_dump_json()

    @abstractmethod
    async def embed(
        self,
        artifact: ChunkArtifact,
    ) -> list[Embedding]:
        """
        Generate canonical embeddings from canonical chunks.

        Args:
            chunks:
                Canonical chunks produced by the Chunking Platform.

        Returns:
            Canonical Embedding objects.
        """
