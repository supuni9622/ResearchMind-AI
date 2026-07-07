"""
Vector Store Platform enumerations.

These enums define the canonical concepts used throughout the Vector
Store Platform.

The Vector Store Platform transforms canonical EmbeddingArtifacts into
searchable vector indexes while remaining independent from any specific
vector database implementation.

Provider SDKs (Qdrant, ChromaDB, Pinecone, pgvector, etc.) remain
implementation details behind the provider abstraction.
"""

from __future__ import annotations

from enum import StrEnum


class VectorStoreProvider(StrEnum):
    """
    Supported vector store providers.

    The provider identifies the implementation registered in the
    VectorStoreRegistry.
    """

    QDRANT = "qdrant"

    CHROMADB = "chromadb"

    PGVECTOR = "pgvector"

    PINECONE = "pinecone"

    WEAVIATE = "weaviate"


class VectorDistanceMetric(StrEnum):
    """
    Supported vector similarity metrics.

    The Embedding Platform recommends which metric should be used for a
    given embedding model. The Vector Store Platform uses that
    recommendation when creating collections.

    Not every provider supports every metric.
    """

    COSINE = "cosine"

    DOT = "dot"

    EUCLIDEAN = "euclidean"


class VectorOperation(StrEnum):
    """
    Supported vector store operations.

    Used for runtime metrics, artifact generation, logging, and future
    observability.
    """

    CREATE_COLLECTION = "create_collection"

    UPSERT = "upsert"

    DELETE = "delete"

    DELETE_DOCUMENT = "delete_document"

    COUNT = "count"

    COLLECTION_INFO = "collection_info"
