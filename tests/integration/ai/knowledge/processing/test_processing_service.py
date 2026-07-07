from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.ai.knowledge.chunking.artifacts.builder import ChunkArtifactBuilder
from app.ai.knowledge.chunking.artifacts.models import ChunkArtifact
from app.ai.knowledge.chunking.factory import create_chunking_service
from app.ai.knowledge.embeddings.artifacts.builder import (
    EmbeddingArtifactBuilder,
)
from app.ai.knowledge.embeddings.enums import EmbeddingProvider
from app.ai.knowledge.embeddings.factory import EmbeddingFactory
from app.ai.knowledge.embeddings.models import Embedding
from app.ai.knowledge.processing.artifact_builder import ArtifactBuilder
from app.ai.knowledge.processing.enums import (
    DocumentFormat,
    ProcessingStatus,
)
from app.ai.knowledge.processing.interfaces import ParseRequest
from app.ai.knowledge.processing.metadata.providers.language import (
    LanguageMetadataProvider,
)
from app.ai.knowledge.processing.metadata.providers.pdf import (
    PDFMetadataProvider,
)
from app.ai.knowledge.processing.metadata.registry import MetadataRegistry
from app.ai.knowledge.processing.metadata.service import (
    MetadataEnrichmentService,
)
from app.ai.knowledge.processing.parsers.docling import DoclingParser
from app.ai.knowledge.processing.registry import ParserRegistry
from app.ai.knowledge.processing.service import ProcessingService
from app.ai.knowledge.processing.statistics.providers.pdf import (
    PDFStatisticsProvider,
)
from app.ai.knowledge.processing.statistics.registry import (
    StatisticsRegistry,
)
from app.ai.knowledge.processing.statistics.service import (
    StatisticsEnrichmentService,
)
from app.ai.knowledge.processing.temporary_file_manager import (
    TemporaryFileManager,
)


@pytest.mark.asyncio
async def test_processing_service_processes_pdf():
    """
    Verify the complete processing pipeline:

    ProcessingService
        ↓
    ParserRegistry
        ↓
    DoclingParser
        ↓
    ProcessedDocument
    """

    registry = ParserRegistry(
        parsers=[
            DoclingParser(),
        ]
    )

    writer = AsyncMock()
    writer.write = AsyncMock(return_value=None)

    chunk_artifact_writer = AsyncMock()
    chunk_artifact_writer.write = AsyncMock(return_value=None)

    embedding_artifact_writer = AsyncMock()
    embedding_artifact_writer.write = AsyncMock(return_value=None)

    def _fake_embed(*, artifact: ChunkArtifact, provider: EmbeddingProvider) -> list[Embedding]:
        return [
            EmbeddingFactory.from_vector(
                chunk=chunk,
                vector=[0.0] * 8,
                provider=provider,
                model="test-voyage-model",
                provider_version="1.0",
                configuration_fingerprint="test-fingerprint",
            )
            for chunk in artifact.chunks
        ]

    embedding_service = AsyncMock()
    embedding_service.embed = AsyncMock(side_effect=_fake_embed)

    storage = AsyncMock()
    storage.download = AsyncMock(
        return_value=Path("tests/fixtures/sample.pdf").read_bytes(),
    )

    metadata_service = MetadataEnrichmentService(
        registry=MetadataRegistry(
            providers=[
                PDFMetadataProvider(),
                LanguageMetadataProvider(),
            ],
        ),
    )

    statistics_service = StatisticsEnrichmentService(
        registry=StatisticsRegistry(
            providers=[
                PDFStatisticsProvider(),
            ],
        ),
    )

    service = ProcessingService(
        storage=storage,
        temporary_file_manager=TemporaryFileManager(),
        parser_registry=registry,
        metadata_service=metadata_service,
        statistics_service=statistics_service,
        artifact_builder=ArtifactBuilder(),
        artifact_writer=writer,
        chunking_service=create_chunking_service(),
        chunk_artifact_builder=ChunkArtifactBuilder(),
        chunk_artifact_writer=chunk_artifact_writer,
        embedding_service=embedding_service,
        embedding_artifact_builder=EmbeddingArtifactBuilder(),
        embedding_artifact_writer=embedding_artifact_writer,
    )

    request = ParseRequest(
        document_id=uuid4(),
        storage_key="tests/fixtures/sample.pdf",
        filename="sample.pdf",
        content_type="application/pdf",
        document_format=DocumentFormat.PDF,
    )

    result = await service.process(owner_id="test-owner", request=request)

    assert result.status == ProcessingStatus.COMPLETED
    assert result.document is not None

    document = result.document

    assert document.format == DocumentFormat.PDF
    assert document.markdown != ""
    assert document.raw_text != ""

    assert document.statistics.character_count > 0
    assert document.statistics.word_count > 0

    # The PDF metadata provider overrides Docling's filename-derived title
    # with the document's actual embedded PDF title.
    assert document.metadata.title == "Buzza MCP ChatGPT Integration - AI Engineering - Confluence"
