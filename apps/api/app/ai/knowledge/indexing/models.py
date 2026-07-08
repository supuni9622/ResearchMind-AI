"""
Canonical Indexing Platform models.

The Indexing Platform orchestrates one or more indexing technologies to
transform embedding artifacts into searchable knowledge indexes.

Unlike the Vector Store Platform, which owns vector indexing,
the Indexing Platform owns orchestration across multiple index types.

Current MVP

- Vector Index (Qdrant)

Future

- BM25
- Knowledge Graph
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.ai.knowledge.chunking.artifacts.models import ChunkArtifact
from app.ai.knowledge.embeddings.artifacts.models import EmbeddingArtifact
from app.ai.knowledge.indexing.enums import IndexOperation, IndexStatus
from app.ai.knowledge.vectorstores.models import (
    CollectionDefinition,
    IndexStatistics,
)

# ============================================================================
# Indexing Execution
# ============================================================================


class IndexingExecution(BaseModel):
    """
    Describes a single indexing execution.
    """

    model_config = ConfigDict(extra="forbid")

    operation: IndexOperation = Field(
        description="Indexing operation being performed.",
    )

    status: IndexStatus = Field(
        default=IndexStatus.PENDING,
        description="Current indexing status.",
    )

    started_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when indexing started.",
    )

    completed_at: datetime | None = Field(
        default=None,
        description="UTC timestamp when indexing completed.",
    )


# ============================================================================
# Indexing Request
# ============================================================================


class IndexingRequest(BaseModel):
    """
    Canonical request received by the Indexing Platform.
    """

    model_config = ConfigDict(extra="forbid")

    owner_id: str = Field(
        description="Owner of the indexed knowledge.",
    )

    operation: IndexOperation = Field(
        default=IndexOperation.CREATE,
        description="Requested indexing operation.",
    )

    embedding_artifact: EmbeddingArtifact = Field(
        description="Embedding artifact to index.",
    )

    chunk_artifact: ChunkArtifact = Field(
        description=(
            "Chunk artifact backing the embedding artifact. Chunk text is "
            "required to generate sparse vectors for hybrid retrieval."
        ),
    )


# ============================================================================
# Indexing Result
# ============================================================================


class IndexingResult(BaseModel):
    """
    Result returned by the Indexing Platform.

    The platform aggregates indexing results from one or more indexing
    technologies.

    Current MVP

    - Vector Index

    Future

    - BM25 Index
    - Knowledge Graph Index
    """

    model_config = ConfigDict(extra="forbid")

    indexing_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this indexing execution.",
    )

    execution: IndexingExecution = Field(
        description="Execution metadata.",
    )

    vector_collection: CollectionDefinition | None = Field(
        default=None,
        description="Definition of the indexed vector collection.",
    )

    vector_statistics: IndexStatistics | None = Field(
        default=None,
        description="Vector indexing statistics.",
    )

    successful_indexes: list[str] = Field(
        default_factory=list,
        description="Successfully indexed targets.",
    )

    failed_indexes: list[str] = Field(
        default_factory=list,
        description="Failed indexing targets.",
    )
