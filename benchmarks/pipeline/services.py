"""
Pipeline benchmark service construction.

Builds the same real, dependency-injected services that
``app.bootstrap.worker.create_processing_worker`` constructs for
production ingestion. The benchmark deliberately reuses these
composition roots instead of constructing providers itself, so it
exercises the real production object graph rather than a parallel one.

No provider is mocked: Chunking, Embedding (Voyage AI), and Indexing
(Qdrant) all run against real infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.ai.knowledge.chunking.artifacts.builder import ChunkArtifactBuilder
from app.ai.knowledge.chunking.artifacts.writer import ChunkArtifactWriter
from app.ai.knowledge.chunking.factory import create_chunking_service
from app.ai.knowledge.chunking.service import ChunkingService
from app.ai.knowledge.embeddings.artifacts.builder import (
    EmbeddingArtifactBuilder,
)
from app.ai.knowledge.embeddings.artifacts.writer import (
    EmbeddingArtifactWriter,
)
from app.ai.knowledge.embeddings.create import create_embedding_service
from app.ai.knowledge.embeddings.service import EmbeddingService
from app.ai.knowledge.indexing.create import create_indexing_service
from app.ai.knowledge.indexing.service import IndexingService
from app.core.settings import settings
from app.infrastructure.storage import create_storage


@dataclass(frozen=True)
class PipelineServices:
    chunking_service: ChunkingService
    chunk_artifact_builder: ChunkArtifactBuilder
    chunk_artifact_writer: ChunkArtifactWriter
    embedding_service: EmbeddingService
    embedding_artifact_builder: EmbeddingArtifactBuilder
    embedding_artifact_writer: EmbeddingArtifactWriter
    indexing_service: IndexingService


def create_pipeline_services() -> PipelineServices:
    """
    Construct the real ingestion services via their production
    composition roots (mirrors ``app.bootstrap.worker``).
    """

    storage = create_storage(settings)

    return PipelineServices(
        chunking_service=create_chunking_service(),
        chunk_artifact_builder=ChunkArtifactBuilder(),
        chunk_artifact_writer=ChunkArtifactWriter(storage),
        embedding_service=create_embedding_service(),
        embedding_artifact_builder=EmbeddingArtifactBuilder(),
        embedding_artifact_writer=EmbeddingArtifactWriter(storage),
        indexing_service=create_indexing_service(),
    )
