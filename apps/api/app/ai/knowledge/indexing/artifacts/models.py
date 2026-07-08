"""
Canonical Indexing Artifact models.

The Indexing Artifact records the outcome of indexing operations performed
by the Indexing Platform.

Unlike the Vector Store Platform, which owns vector indexing details,
the Indexing Platform owns the orchestration and execution history of
all indexing technologies.

Current MVP

- Vector Index

Future

- BM25
- Knowledge Graph
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.ai.knowledge.indexing.enums import IndexStatus
from app.ai.knowledge.vectorstores.models import (
    CollectionDefinition,
    IndexStatistics,
)
from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# Execution Metadata
# ============================================================================


class IndexingArtifactExecution(BaseModel):
    """
    Execution metadata for an indexing operation.
    """

    model_config = ConfigDict(extra="forbid")

    execution_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this indexing execution.",
    )

    started_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when indexing started.",
    )

    completed_at: datetime = Field(
        description="UTC timestamp when indexing completed.",
    )

    duration_ms: float = Field(
        ge=0,
        description="Total indexing duration in milliseconds.",
    )
    status: IndexStatus = Field(
        description="Final execution status.",
    )


# ============================================================================
# Vector Index Artifact
# ============================================================================


class VectorIndexArtifact(BaseModel):
    """
    Artifact describing a completed vector indexing operation.
    """

    model_config = ConfigDict(extra="forbid")

    collection: CollectionDefinition = Field(
        description="Definition of the indexed vector collection.",
    )

    statistics: IndexStatistics = Field(
        description="Statistics produced during vector indexing.",
    )


# ============================================================================
# Indexing Artifact
# ============================================================================


class IndexingArtifact(BaseModel):
    """
    Canonical artifact produced by the Indexing Platform.

    This artifact records the outcome of a complete indexing execution.

    Current MVP

    - Vector Index

    Future

    - BM25 Index
    - Knowledge Graph Index
    """

    model_config = ConfigDict(extra="forbid")

    execution: IndexingArtifactExecution = Field(
        description="Execution metadata.",
    )

    vector_index: VectorIndexArtifact | None = Field(
        default=None,
        description="Vector indexing artifact.",
    )
