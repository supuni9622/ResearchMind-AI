"""
Vector Store provider interfaces.

Every vector store implementation (Qdrant, ChromaDB, Pinecone,
pgvector, Weaviate, etc.) must implement this interface.

The VectorStoreService depends only on this interface, allowing vector
database providers to be replaced without changing application code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel

from app.ai.knowledge.vectorstores.enums import VectorStoreProvider
from app.ai.knowledge.vectorstores.models import (
    CollectionDefinition,
    CollectionMetadata,
    VectorStoreRecord,
)


class VectorStoreProviderInterface(ABC):
    """
    Base interface for every vector store provider.
    """

    @property
    @abstractmethod
    def provider(self) -> VectorStoreProvider:
        """
        Provider identifier.
        """

    @property
    @abstractmethod
    def version(self) -> str:
        """
        Version of the provider implementation.

        Used for reproducibility, observability, and future
        experimentation.
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
        Stable fingerprint uniquely identifying the provider
        configuration.
        """

        return self.config.model_dump_json()

    @abstractmethod
    async def create_collection(
        self,
        collection: CollectionDefinition,
    ) -> None:
        """
        Create a vector collection.

        Raises:
            CollectionAlreadyExistsError
        """

    @abstractmethod
    async def collection_exists(
        self,
        collection_name: str,
    ) -> bool:
        """
        Determine whether a collection exists.
        """

    @abstractmethod
    async def upsert(
        self,
        *,
        collection_name: str,
        records: list[VectorStoreRecord],
    ) -> None:
        """
        Index vector records into a collection.

        Existing vectors should be replaced if the same identifier
        already exists.
        """

    @abstractmethod
    async def delete_document(
        self,
        *,
        collection_name: str,
        document_id: str,
    ) -> None:
        """
        Delete all vectors belonging to a document.
        """

    @abstractmethod
    async def count(
        self,
        collection_name: str,
    ) -> int:
        """
        Return the total number of indexed vectors.
        """

    @abstractmethod
    async def collection_info(
        self,
        collection_name: str,
    ) -> CollectionMetadata:
        """
        Return metadata describing the collection.
        """
