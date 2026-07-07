"""
Qdrant Vector Store provider.

This provider persists canonical VectorStoreRecord objects in Qdrant
while exposing only canonical domain models to the rest of the
Knowledge Platform.

Qdrant SDK types never leak outside this provider.
"""

from __future__ import annotations

import structlog
from app.ai.knowledge.vectorstores.base import BaseVectorStoreProvider
from app.ai.knowledge.vectorstores.config import (
    QdrantVectorStoreConfig,
)
from app.ai.knowledge.vectorstores.enums import (
    VectorDistanceMetric,
    VectorStoreProvider,
)
from app.ai.knowledge.vectorstores.exceptions import (
    CollectionAlreadyExistsError,
    CollectionNotFoundError,
    CollectionOperationError,
    VectorDeletionError,
    VectorIndexingError,
)
from app.ai.knowledge.vectorstores.models import (
    CollectionDefinition,
    CollectionMetadata,
    VectorStoreRecord,
)
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qdrant

logger = structlog.get_logger()


class QdrantVectorStoreProvider(
    BaseVectorStoreProvider[QdrantVectorStoreConfig],
):
    """
    Qdrant implementation of the Vector Store Platform.
    """

    def __init__(
        self,
        config: QdrantVectorStoreConfig,
        client: AsyncQdrantClient,
    ) -> None:
        super().__init__(config)

        self._client = client

    @property
    def provider(self) -> VectorStoreProvider:
        """
        Provider identifier.
        """

        return VectorStoreProvider.QDRANT

    async def create_collection(
        self,
        definition: CollectionDefinition,
    ) -> None:
        """
        Create a Qdrant collection.
        """

        logger.info(
            "vectorstore.qdrant.create_collection.started",
            collection=definition.name,
            dimensions=definition.dimensions,
            distance_metric=definition.distance_metric.value,
        )

        if await self.collection_exists(definition.name):
            raise CollectionAlreadyExistsError(f"Collection '{definition.name}' already exists.")

        await self._client.create_collection(
            collection_name=definition.name,
            vectors_config=qdrant.VectorParams(
                size=definition.dimensions,
                distance=self._to_distance(
                    definition.distance_metric,
                ),
            ),
            hnsw_config=qdrant.HnswConfigDiff(
                m=self.config.hnsw_m,
                ef_construct=self.config.hnsw_ef_construct,
            ),
            on_disk_payload=self.config.on_disk_payload,
        )

        logger.info(
            "vectorstore.qdrant.create_collection.completed",
            collection=definition.name,
        )

    async def collection_exists(
        self,
        collection_name: str,
    ) -> bool:
        """
        Determine whether a collection exists.
        """

        # collections = await self._client.get_collections()
        # return any(
        #     collection.name == collection_name
        #     for collection in collections.collections
        # )
        return await self._client.collection_exists(collection_name)

    @staticmethod
    def _to_distance(
        metric: VectorDistanceMetric,
    ) -> qdrant.Distance:
        """
        Convert the canonical distance metric into the corresponding
        Qdrant distance enum.
        """

        mapping = {
            VectorDistanceMetric.COSINE: qdrant.Distance.COSINE,
            VectorDistanceMetric.DOT: qdrant.Distance.DOT,
            VectorDistanceMetric.EUCLIDEAN: qdrant.Distance.EUCLID,
        }

        return mapping[metric]

    @staticmethod
    def _from_distance(
        distance: qdrant.Distance,
    ) -> VectorDistanceMetric:
        """
        Convert a Qdrant distance enum into the corresponding canonical
        distance metric.
        """

        mapping = {
            qdrant.Distance.COSINE: VectorDistanceMetric.COSINE,
            qdrant.Distance.DOT: VectorDistanceMetric.DOT,
            qdrant.Distance.EUCLID: VectorDistanceMetric.EUCLIDEAN,
        }

        return mapping[distance]

    @staticmethod
    def _to_point(
        record: VectorStoreRecord,
    ) -> qdrant.PointStruct:
        """
        Convert a canonical VectorStoreRecord into a Qdrant PointStruct.
        """

        return qdrant.PointStruct(
            id=str(record.id),
            vector=record.vector,
            payload=record.payload.model_dump(
                mode="json",
                exclude_none=True,
            ),
        )

    async def upsert(
        self,
        *,
        collection_name: str,
        records: list[VectorStoreRecord],
    ) -> None:
        """
        Index vector records into Qdrant.

        Existing vectors with the same identifier will be replaced.
        """

        logger.info(
            "vectorstore.qdrant.upsert.started",
            collection=collection_name,
            vectors=len(records),
        )

        try:
            batch_size = self.config.batch_size

            for start in range(0, len(records), batch_size):
                batch = records[start : start + batch_size]

                await self._client.upsert(
                    collection_name=collection_name,
                    points=[self._to_point(record) for record in batch],
                    wait=self.config.wait_for_indexing,
                )

        except Exception as exc:
            logger.exception(
                "vectorstore.qdrant.upsert.failed",
                collection=collection_name,
            )

            raise VectorIndexingError(
                f"Failed to index vectors into collection '{collection_name}'."
            ) from exc

        logger.info(
            "vectorstore.qdrant.upsert.completed",
            collection=collection_name,
            vectors=len(records),
        )

    async def delete_document(
        self,
        *,
        collection_name: str,
        document_id: str,
    ) -> None:
        """
        Delete every vector belonging to a document.
        """

        logger.info(
            "vectorstore.qdrant.delete_document.started",
            collection=collection_name,
            document_id=document_id,
        )

        try:
            await self._client.delete(
                collection_name=collection_name,
                points_selector=qdrant.FilterSelector(
                    filter=qdrant.Filter(
                        must=[
                            qdrant.FieldCondition(
                                key="document_id",
                                match=qdrant.MatchValue(
                                    value=document_id,
                                ),
                            ),
                        ],
                    ),
                ),
                wait=self.config.wait_for_indexing,
            )

        except Exception as exc:
            logger.exception(
                "vectorstore.qdrant.delete_document.failed",
                collection=collection_name,
                document_id=document_id,
            )

            raise VectorDeletionError(
                f"Failed to delete vectors for document '{document_id}'."
            ) from exc

        logger.info(
            "vectorstore.qdrant.delete_document.completed",
            collection=collection_name,
            document_id=document_id,
        )

    async def count(
        self,
        collection_name: str,
    ) -> int:
        """
        Return the number of indexed vectors.
        """

        try:
            response = await self._client.count(
                collection_name=collection_name,
                exact=True,
            )

            return response.count

        except Exception as exc:
            logger.exception(
                "vectorstore.qdrant.count.failed",
                collection=collection_name,
            )

            raise CollectionOperationError(
                f"Failed to count vectors in '{collection_name}'."
            ) from exc

    async def collection_info(
        self,
        collection_name: str,
    ) -> CollectionMetadata:
        """
        Return metadata describing a collection.
        """

        try:
            info = await self._client.get_collection(
                collection_name,
            )

        except Exception as exc:
            logger.exception(
                "vectorstore.qdrant.collection_info.failed",
                collection=collection_name,
            )

            raise CollectionNotFoundError(f"Collection '{collection_name}' was not found.") from exc

        vectors = info.config.params.vectors

        if not isinstance(vectors, qdrant.VectorParams):
            raise CollectionOperationError(
                f"Collection '{collection_name}' does not use a single unnamed vector "
                "configuration."
            )

        return CollectionMetadata(
            definition=CollectionDefinition(
                name=collection_name,
                provider=self.provider,
                dimensions=vectors.size,
                distance_metric=self._from_distance(vectors.distance),
            ),
            vector_count=info.points_count or 0,
        )
