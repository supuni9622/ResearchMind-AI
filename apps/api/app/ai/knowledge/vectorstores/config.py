"""
Vector Store configuration models.

These configuration models define the behavior of vector store providers.

The Vector Store Platform intentionally separates provider configuration
from provider implementation to support reproducibility,
experimentation, and future provider versioning.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.ai.knowledge.vectorstores.enums import VectorDistanceMetric


class BaseVectorStoreConfig(BaseModel):
    """
    Base configuration shared by all vector store providers.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    batch_size: int = Field(
        default=100,
        ge=1,
        description="Maximum number of vectors indexed per batch.",
    )

    create_collection_if_missing: bool = Field(
        default=True,
        description="Automatically create collections if they do not exist.",
    )


class QdrantVectorStoreConfig(BaseVectorStoreConfig):
    """
    Configuration for the Qdrant vector store provider.
    """

    collection_name: str = Field(
        default="knowledge",
        description="Default Qdrant collection name.",
    )

    distance_metric: VectorDistanceMetric = Field(
        default=VectorDistanceMetric.DOT,
        description="Distance metric used when creating collections.",
    )

    hnsw_m: int = Field(
        default=16,
        ge=4,
        description="HNSW M parameter.",
    )

    hnsw_ef_construct: int = Field(
        default=100,
        ge=8,
        description="HNSW ef_construct parameter.",
    )

    on_disk_payload: bool = Field(
        default=True,
        description="Store payload on disk to reduce memory usage.",
    )
    create_payload_indexes: bool = True
    wait_for_indexing: bool = True


class ChromaVectorStoreConfig(BaseVectorStoreConfig):
    """
    Configuration for the ChromaDB provider.
    """

    collection_name: str = Field(
        default="researchmind",
    )


class PgVectorStoreConfig(BaseVectorStoreConfig):
    """
    Configuration for the pgvector provider.
    """

    table_name: str = Field(
        default="embeddings",
    )


class PineconeVectorStoreConfig(BaseVectorStoreConfig):
    """
    Configuration for the Pinecone provider.
    """

    index_name: str = Field(
        default="researchmind",
    )


class WeaviateVectorStoreConfig(BaseVectorStoreConfig):
    """
    Configuration for the Weaviate provider.
    """

    collection_name: str = Field(
        default="researchmind",
    )
