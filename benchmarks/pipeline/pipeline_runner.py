"""
Executes the real ingestion pipeline for a single benchmark document.

Stages executed, in order, against real production services:

    Chunking -> Embedding (Voyage AI) -> Indexing (Qdrant) -> Persist Artifacts

Upload and Processing (PDF parsing) are intentionally not re-executed.
The benchmark dataset stores documents as ``ProcessedDocument`` JSON,
the same canonical artifact the real Processing Platform would have
produced from an uploaded PDF (see benchmarks/datasets/README.md).
Every stage from Chunking onward runs unmocked, through the same
services and artifact builders/writers production uses.

Runtime instrumentation reuses ``RuntimeMetricsCollector``, the same
runtime metrics collector wired into ``ProcessingService`` in
production, rather than a benchmark-specific timer.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from app.ai.knowledge.chunking.enums import ChunkingStrategy
from app.ai.knowledge.embeddings.enums import EmbeddingProvider
from app.ai.knowledge.indexing.artifacts.builder import (
    IndexingArtifactBuilder,
)
from app.ai.knowledge.indexing.artifacts.models import (
    IndexingArtifactExecution,
)
from app.ai.knowledge.indexing.models import IndexingRequest
from app.ai.knowledge.processing.models import ProcessedDocument
from app.ai.observability.runtime import RuntimeMetricsCollector

from benchmarks.pipeline.models import (
    ArtifactSizes,
    ChunkingMetrics,
    DocumentInfo,
    DocumentPipelineResult,
    EmbeddingMetrics,
    IndexingMetrics,
)
from benchmarks.pipeline.services import PipelineServices

# Matches the only active strategy/provider in
# ProcessingService._execute_chunking_stage / _execute_embedding_stage.
CHUNKING_STRATEGY = ChunkingStrategy.MARKDOWN
EMBEDDING_PROVIDER = EmbeddingProvider.VOYAGE_AI


async def run_document_pipeline(
    *,
    document: ProcessedDocument,
    source_size_bytes: int,
    services: PipelineServices,
    owner_id: str,
    on_progress: Callable[[str], None] | None = None,
) -> DocumentPipelineResult:
    """
    Run one document through the real Chunking -> Embedding -> Indexing
    -> Persist Artifacts pipeline and collect production runtime metrics.
    """

    def progress(message: str) -> None:
        if on_progress is not None:
            on_progress(message)

    runtime = RuntimeMetricsCollector()
    runtime.start_pipeline()

    progress("  chunking...")
    runtime.start_stage("Chunking")
    chunks = await services.chunking_service.chunk(
        document=document,
        strategy=CHUNKING_STRATEGY,
    )
    chunk_artifact = services.chunk_artifact_builder.build(chunks)
    runtime.finish_stage()

    chunks_json_bytes = len(
        chunk_artifact.model_dump_json(
            indent=2,
            exclude_none=True,
        ).encode("utf-8")
    )
    runtime.add_artifact("chunks.json", chunks_json_bytes)

    await services.chunk_artifact_writer.write(
        owner_id=owner_id,
        artifact=chunk_artifact,
    )
    progress(f"  chunking done ({chunk_artifact.statistics.total_chunks} chunks)")

    progress("  embedding (Voyage AI)...")
    runtime.start_stage("Embedding")
    embeddings = await services.embedding_service.embed(
        artifact=chunk_artifact,
        provider=EMBEDDING_PROVIDER,
    )
    embedding_artifact = services.embedding_artifact_builder.build(
        chunk_artifact=chunk_artifact,
        embeddings=embeddings,
    )
    runtime.finish_stage()

    embeddings_json_bytes = len(
        embedding_artifact.model_dump_json(
            indent=2,
            exclude_none=True,
        ).encode("utf-8")
    )
    runtime.add_artifact("embeddings.json", embeddings_json_bytes)

    await services.embedding_artifact_writer.write(
        owner_id=owner_id,
        artifact=embedding_artifact,
    )
    progress(f"  embedding done ({embedding_artifact.statistics.total_embeddings} vectors)")

    progress("  indexing (Qdrant)...")
    runtime.start_stage("Indexing")
    result = await services.indexing_service.index(
        IndexingRequest(
            owner_id=owner_id,
            embedding_artifact=embedding_artifact,
        )
    )
    runtime.finish_stage()

    if result.vector_statistics is None or result.vector_collection is None:
        raise RuntimeError(f"Indexing produced no vector statistics for '{document.filename}'.")

    indexing_artifact = IndexingArtifactBuilder.build(
        execution=IndexingArtifactExecution(
            started_at=result.execution.started_at,
            completed_at=result.execution.completed_at or datetime.now(UTC),
            duration_ms=result.vector_statistics.duration_ms,
            status=result.execution.status,
        ),
        result=result,
    )
    indexing_json_bytes = len(
        indexing_artifact.model_dump_json(
            indent=2,
            exclude_none=True,
        ).encode("utf-8")
    )
    runtime.add_artifact("indexing.json", indexing_json_bytes)
    runtime.add_artifact("processed_document.json", source_size_bytes)
    progress(f"  indexing done ({result.vector_statistics.indexed_vectors} vectors)")

    metrics = runtime.finish_pipeline()
    stage_duration_ms = {stage.stage: stage.duration_ms for stage in metrics.stages}

    return DocumentPipelineResult(
        document=DocumentInfo(
            filename=document.filename,
            source_size_bytes=source_size_bytes,
            page_count=document.statistics.page_count,
            character_count=document.statistics.character_count,
            word_count=document.statistics.word_count,
        ),
        chunking=ChunkingMetrics(
            chunk_count=chunk_artifact.statistics.total_chunks,
            average_chunk_size=chunk_artifact.statistics.average_chunk_size,
            largest_chunk=max(chunk.statistics.character_count for chunk in chunks),
            smallest_chunk=min(chunk.statistics.character_count for chunk in chunks),
            duration_ms=stage_duration_ms["Chunking"],
        ),
        embedding=EmbeddingMetrics(
            embedding_count=embedding_artifact.statistics.total_embeddings,
            dimensions=embedding_artifact.statistics.dimensions,
            duration_ms=stage_duration_ms["Embedding"],
            provider=embedding_artifact.execution.provider.value,
            model=embedding_artifact.execution.model,
        ),
        indexing=IndexingMetrics(
            vector_count=result.vector_statistics.indexed_vectors,
            duration_ms=stage_duration_ms["Indexing"],
            collection_name=result.vector_collection.name,
        ),
        artifacts=ArtifactSizes(
            processed_document_json_bytes=source_size_bytes,
            chunks_json_bytes=chunks_json_bytes,
            embeddings_json_bytes=embeddings_json_bytes,
            indexing_json_bytes=indexing_json_bytes,
        ),
        total_duration_ms=metrics.total_duration_ms,
        peak_memory_mb=metrics.peak_memory_mb,
    )
