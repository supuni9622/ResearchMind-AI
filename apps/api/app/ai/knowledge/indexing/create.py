"""
Indexing Platform composition root.

Assembles the Indexing Platform by constructing the IndexingService and
injecting its dependencies.

This module is the single composition root for the Indexing Platform.

Future indexing technologies (BM25, Knowledge Graph, etc.) should be
registered here without modifying the rest of the application.
"""

from __future__ import annotations

from app.ai.knowledge.indexing.artifacts.writer import (
    IndexingArtifactWriter,
)
from app.ai.knowledge.indexing.service import (
    IndexingService,
)
from app.ai.knowledge.vectorstores.create import (
    create_vectorstore_service,
)
from app.core.settings import settings
from app.infrastructure.storage import create_storage


def create_indexing_artifact_writer() -> IndexingArtifactWriter:
    """
    Create a fully configured IndexingArtifactWriter.
    """

    return IndexingArtifactWriter(
        storage_provider=create_storage(settings),
    )


def create_indexing_service() -> IndexingService:
    """
    Create a fully configured IndexingService.
    """

    return IndexingService(
        vectorstore_service=create_vectorstore_service(),
        artifact_writer=create_indexing_artifact_writer(),
    )
