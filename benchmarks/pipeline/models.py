"""
Ingestion Pipeline Benchmark models.

Canonical models describing the outcome of benchmarking the complete
ResearchMind ingestion pipeline end-to-end.

Unlike ``benchmarks.models.report.BenchmarkReport`` (which compares
multiple named candidates against one shared metric table), the
Pipeline Benchmark pushes every document through the *same* real
ingestion services and reports rich per-document, aggregate, storage,
throughput, and memory characteristics. That shape does not fit the
candidate-comparison model, so it gets its own report models here.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# Per-document metrics
# ============================================================================


class DocumentInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str
    source_size_bytes: int
    page_count: int
    character_count: int
    word_count: int


class ChunkingMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_count: int
    average_chunk_size: float
    largest_chunk: int
    smallest_chunk: int
    duration_ms: float


class EmbeddingMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    embedding_count: int
    dimensions: int
    duration_ms: float
    provider: str
    model: str


class IndexingMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vector_count: int
    duration_ms: float
    collection_name: str


class ArtifactSizes(BaseModel):
    model_config = ConfigDict(extra="forbid")

    processed_document_json_bytes: int
    chunks_json_bytes: int
    embeddings_json_bytes: int
    indexing_json_bytes: int

    @property
    def total_bytes(self) -> int:
        return (
            self.processed_document_json_bytes
            + self.chunks_json_bytes
            + self.embeddings_json_bytes
            + self.indexing_json_bytes
        )


class DocumentPipelineResult(BaseModel):
    """
    Complete benchmark result for a single document.
    """

    model_config = ConfigDict(extra="forbid")

    document: DocumentInfo
    chunking: ChunkingMetrics
    embedding: EmbeddingMetrics
    indexing: IndexingMetrics
    artifacts: ArtifactSizes
    total_duration_ms: float
    peak_memory_mb: float


# ============================================================================
# Aggregate metrics
# ============================================================================


class StatSummary(BaseModel):
    """
    Average / Minimum / Maximum / Median / P95 for one measured metric.
    """

    model_config = ConfigDict(extra="forbid")

    average: float
    minimum: float
    maximum: float
    median: float
    p95: float


class ThroughputSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    documents_per_minute: float
    chunks_per_second: float
    embeddings_per_second: float
    vectors_per_second: float


class StorageSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    average_bytes_per_document: float
    average_bytes_per_chunk: float
    average_bytes_per_embedding: float
    total_bytes_generated: int
    average_processed_document_json_bytes: float
    average_chunks_json_bytes: float
    average_embeddings_json_bytes: float
    average_indexing_json_bytes: float


class MemorySummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    average_peak_memory_mb: float
    minimum_peak_memory_mb: float
    maximum_peak_memory_mb: float


class SuccessReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    documents_processed: int
    successful: int
    failed: int
    success_rate: float


class Observations(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slowest_document: str
    slowest_document_duration_ms: float
    fastest_document: str
    fastest_document_duration_ms: float
    largest_artifact: str
    largest_artifact_bytes: int
    smallest_artifact: str
    smallest_artifact_bytes: int
    average_pipeline_time_ms: float
    average_vectors_generated: float
    average_chunks_generated: float


class ProductionReadiness(BaseModel):
    model_config = ConfigDict(extra="forbid")

    checks: list[str]
    recommendations: list[str]


# ============================================================================
# Report
# ============================================================================


class PipelineBenchmarkReport(BaseModel):
    """
    Canonical report produced by the Ingestion Pipeline Benchmark.
    """

    model_config = ConfigDict(extra="forbid")

    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    commit: str | None = None

    environment: dict[str, str] = Field(default_factory=dict)

    dataset_name: str
    dataset_directory: str

    documents: list[DocumentPipelineResult]

    pipeline_timing: dict[str, StatSummary]
    aggregate_statistics: dict[str, StatSummary]

    throughput: ThroughputSummary
    storage: StorageSummary
    memory: MemorySummary
    success: SuccessReport
    observations: Observations
    production_readiness: ProductionReadiness
