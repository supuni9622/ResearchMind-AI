"""
Application composition root.

This module constructs object graphs that are shared between
multiple application entry points (API, workers, CLI, etc.).
"""

from __future__ import annotations

from app.ai.knowledge.processing.artifact_builder import ArtifactBuilder
from app.ai.knowledge.processing.artifact_writer import ArtifactWriter
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
from app.ai.knowledge.processing.parsers import DoclingParser
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
from app.core.settings import settings
from app.infrastructure.queue.factory import create_processing_queue
from app.infrastructure.storage import create_storage
from app.repositories.document import DocumentRepository
from app.services.document_processing_service import (
    DocumentProcessingService,
)
from app.services.queued_document_processing_service import (
    QueuedDocumentProcessingService,
)
from sqlalchemy.ext.asyncio import AsyncSession

from apps.worker.processing_worker import ProcessingWorker


def create_processing_worker(
    *,
    session: AsyncSession,
) -> ProcessingWorker:
    """
    Construct the processing worker object graph.
    """

    storage = create_storage(settings)

    parser_registry = ParserRegistry(
        parsers=[
            DoclingParser(),
        ],
    )

    metadata_registry = MetadataRegistry()
    metadata_registry.register(PDFMetadataProvider())
    metadata_registry.register(LanguageMetadataProvider())

    statistics_registry = StatisticsRegistry()
    statistics_registry.register(PDFStatisticsProvider())

    processing_service = ProcessingService(
        storage=storage,
        temporary_file_manager=TemporaryFileManager(),
        parser_registry=parser_registry,
        metadata_service=MetadataEnrichmentService(
            registry=metadata_registry,
        ),
        statistics_service=StatisticsEnrichmentService(
            registry=statistics_registry,
        ),
        artifact_builder=ArtifactBuilder(),
        artifact_writer=ArtifactWriter(storage),
    )

    repository = DocumentRepository(session)

    document_processing_service = DocumentProcessingService(
        processing_service=processing_service,
        document_repository=repository,
        session=session,
    )

    queued_document_processing_service = QueuedDocumentProcessingService(
        document_processing_service=document_processing_service,
        document_repository=repository,
    )

    return ProcessingWorker(
        queue=create_processing_queue(settings),
        queued_document_processing_service=(queued_document_processing_service),
    )
