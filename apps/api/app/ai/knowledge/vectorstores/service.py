"""
Vector Store service.

The VectorStoreService orchestrates vector indexing.

It is responsible for:

- validating inputs
- resolving the requested vector store provider
- delegating vector indexing operations

The service contains no provider-specific logic.

Concrete vector database operations live entirely inside provider
implementations.
"""

from __future__ import annotations

from app.ai.knowledge.vectorstores.enums import VectorStoreProvider
from app.ai.knowledge.vectorstores.exceptions import (
    VectorStoreValidationError,
)
from app.ai.knowledge.vectorstores.models import (
    CollectionDefinition,
    CollectionMetadata,
    VectorStoreRecord,
)
from app.ai.knowledge.vectorstores.registry import (
    VectorStoreRegistry,
)


class VectorStoreService:
    """
    Orchestrates vector indexing.

    The service depends only on the VectorStoreRegistry. This keeps the
    orchestration layer independent from concrete vector store
    implementations.
    """

    def __init__(
        self,
        registry: VectorStoreRegistry,
    ) -> None:
        self._registry = registry

    async def create_collection(
        self,
        *,
        provider: VectorStoreProvider,
        definition: CollectionDefinition,
    ) -> None:
        """
        Create a collection if required.
        """

        vector_provider = self._registry.get(provider)

        await vector_provider.create_collection(definition)

    async def collection_exists(
        self,
        *,
        provider: VectorStoreProvider,
        collection_name: str,
    ) -> bool:
        """
        Determine whether a collection exists.
        """

        vector_provider = self._registry.get(provider)

        return await vector_provider.collection_exists(collection_name)

    async def upsert(
        self,
        *,
        provider: VectorStoreProvider,
        collection_name: str,
        records: list[VectorStoreRecord],
    ) -> None:
        """
        Index vector records into a collection.
        """

        self._validate(records)

        vector_provider = self._registry.get(provider)

        await vector_provider.upsert(
            collection_name=collection_name,
            records=records,
        )

    async def delete_document(
        self,
        *,
        provider: VectorStoreProvider,
        collection_name: str,
        document_id: str,
    ) -> None:
        """
        Delete all vectors belonging to a document.
        """

        vector_provider = self._registry.get(provider)

        await vector_provider.delete_document(
            collection_name=collection_name,
            document_id=document_id,
        )

    async def count(
        self,
        *,
        provider: VectorStoreProvider,
        collection_name: str,
    ) -> int:
        """
        Return the number of indexed vectors.
        """

        vector_provider = self._registry.get(provider)

        return await vector_provider.count(collection_name)

    async def collection_info(
        self,
        *,
        provider: VectorStoreProvider,
        collection_name: str,
    ) -> CollectionMetadata:
        """
        Return collection metadata.
        """

        vector_provider = self._registry.get(provider)

        return await vector_provider.collection_info(collection_name)

    @staticmethod
    def _validate(
        records: list[VectorStoreRecord],
    ) -> None:
        """
        Validate vector records before indexing.
        """

        if not records:
            raise VectorStoreValidationError("No vector records were provided for indexing.")

        for record in records:
            if not record.vector:
                raise VectorStoreValidationError(f"Vector '{record.id}' contains no values.")
