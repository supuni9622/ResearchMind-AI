"""
Indexing Artifact Builder.

Transforms canonical indexing models into immutable indexing artifacts.

The builder contains no business logic and performs no persistence.
"""

from __future__ import annotations

from app.ai.knowledge.indexing.artifacts.models import (
    IndexingArtifact,
    IndexingArtifactExecution,
    VectorIndexArtifact,
)
from app.ai.knowledge.indexing.models import IndexingResult


class IndexingArtifactBuilder:
    """
    Builds immutable IndexingArtifact instances.

    The builder is responsible only for transforming canonical indexing
    models into artifact models.
    """

    @staticmethod
    def build(
        *,
        execution: IndexingArtifactExecution,
        result: IndexingResult,
    ) -> IndexingArtifact:
        """
        Build an IndexingArtifact.

        Parameters
        ----------
        execution
            Execution metadata for this indexing operation.

        result
            Result produced by the Indexing Platform.

        Returns
        -------
        IndexingArtifact
        """

        vector_index = None

        if result.vector_collection is not None and result.vector_statistics is not None:
            vector_index = VectorIndexArtifact(
                collection=result.vector_collection,
                statistics=result.vector_statistics,
            )

        return IndexingArtifact(
            execution=execution,
            vector_index=vector_index,
        )
