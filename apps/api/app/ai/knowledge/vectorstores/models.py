"""
Canonical Vector Store models.

The Vector Store Platform transforms canonical Embeddings into searchable
vector indexes while remaining independent from any vector database
implementation.

These models define the canonical domain objects shared throughout the
Vector Store Platform. Provider SDK objects (Qdrant, ChromaDB,
Pinecone, etc.) must never leak outside provider implementations.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.ai.knowledge.vectorstores.enums import (
    VectorDistanceMetric,
    VectorStoreProvider,
)

# ============================================================================
# Payload
# ============================================================================


class VectorPayload(BaseModel):
    """
    Metadata stored alongside a vector.

    This payload enables filtering, authorization, citations, and future
    retrieval strategies without exposing provider-specific payload
    implementations.
    """

    model_config = ConfigDict(extra="forbid")

    document_id: UUID = Field(
        description="Source document identifier.",
    )

    chunk_id: UUID = Field(
        description="Source chunk identifier.",
    )

    filename: str = Field(
        description="Original filename.",
    )

    owner_id: str = Field(
        description="Owner of the indexed document.",
    )

    chunk_index: int = Field(
        ge=0,
        description="Chunk position within the document.",
    )

    language: str | None = Field(
        default=None,
        description="Document language.",
    )

    additional_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional provider-independent metadata.",
    )


# ============================================================================
# Sparse Vector
# ============================================================================


class SparseVector(BaseModel):
    """
    Sparse neural vector representing lexical signal for a chunk.

    Produced by FastEmbed SPLADE and indexed alongside the dense vector
    so that Qdrant can perform native hybrid retrieval without a
    separate BM25 platform (see ADR-019).
    """

    model_config = ConfigDict(extra="forbid")

    indices: list[int] = Field(
        description="Non-zero term indices in the sparse vocabulary.",
    )

    values: list[float] = Field(
        description="Weights corresponding to each non-zero term index.",
    )


# ============================================================================
# Vector Record
# ============================================================================


class VectorStoreRecord(BaseModel):
    """
    Canonical vector record.

    Represents one vector ready to be indexed into a vector database.
    """

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(
        description="Unique vector identifier.",
    )

    vector: list[float] = Field(
        description="Embedding vector values.",
    )

    sparse_vector: SparseVector | None = Field(
        default=None,
        description="Sparse vector enabling hybrid retrieval, when available.",
    )

    payload: VectorPayload


class CollectionDefinition(BaseModel):
    """
    Definition used to create a vector collection.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        description="Collection name.",
    )

    provider: VectorStoreProvider = Field(
        description="Vector store provider.",
    )

    dimensions: int = Field(
        gt=0,
        description="Embedding vector dimensions.",
    )

    distance_metric: VectorDistanceMetric = Field(
        description="Similarity metric used by the collection.",
    )


# ============================================================================
# Collection Metadata
# ============================================================================


class CollectionMetadata(BaseModel):
    """
    Metadata describing an existing collection.
    """

    model_config = ConfigDict(extra="forbid")

    definition: CollectionDefinition

    vector_count: int = Field(
        default=0,
        ge=0,
        description="Number of indexed vectors.",
    )


# ============================================================================
# Index Statistics
# ============================================================================


class IndexStatistics(BaseModel):
    """
    Statistics describing a single indexing execution.
    """

    model_config = ConfigDict(extra="forbid")

    indexed_vectors: int = Field(
        default=0,
        ge=0,
        description="Successfully indexed vectors.",
    )

    failed_vectors: int = Field(
        default=0,
        ge=0,
        description="Vectors that failed to index.",
    )

    indexed_sparse_vectors: int = Field(
        default=0,
        ge=0,
        description="Successfully indexed sparse vectors.",
    )

    batch_size: int = Field(
        gt=0,
        description="Batch size used during indexing.",
    )

    duration_ms: float = Field(
        ge=0,
        description="Indexing duration in milliseconds.",
    )
