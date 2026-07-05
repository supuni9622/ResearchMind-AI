"""
Dependency providers for the document upload and processing workflow.
"""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.knowledge.chunking.artifacts.builder import ChunkArtifactBuilder
from app.ai.knowledge.chunking.artifacts.writer import ChunkArtifactWriter
from app.ai.knowledge.chunking.factory import create_chunking_service
from app.ai.knowledge.chunking.service import ChunkingService
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
from app.ai.knowledge.upload.duplicate.service import (
    DuplicateDetectionService,
)
from app.ai.knowledge.upload.service import UploadService
from app.core.settings import settings
from app.db.session import get_db
from app.infrastructure.hashing import FileHasher, SHA256Hasher
from app.infrastructure.queue.factory import (
    create_processing_queue,
)
from app.infrastructure.queue.interfaces import (
    ProcessingQueue,
)
from app.infrastructure.storage import DocumentStorage, create_storage
from app.repositories.document import DocumentRepository
from app.services.document_processing_service import (
    DocumentProcessingService,
)
from app.services.queued_document_processing_service import (
    QueuedDocumentProcessingService,
)
from apps.worker.processing_worker import ProcessingWorker


def _get_storage() -> DocumentStorage:
    """
    Create the configured document storage service.

    The instance is cached because it is stateless and
    safe to reuse across requests.
    """

    return create_storage(settings)


@lru_cache
def _get_processing_queue() -> ProcessingQueue:
    """
    Create the configured processing queue.

    The queue implementation is selected from configuration.
    """

    return create_processing_queue(settings)


@lru_cache
def _get_hasher() -> FileHasher:
    """
    Create the configured file hasher.
    """

    return SHA256Hasher()


@lru_cache
def _get_parser_registry() -> ParserRegistry:
    """
    Create the parser registry.

    Parser implementations are stateless and safe to reuse.
    """

    return ParserRegistry(
        parsers=[
            DoclingParser(),
        ],
    )


@lru_cache
def _get_metadata_registry() -> MetadataRegistry:
    """
    Create the metadata provider registry.

    Provider implementations are stateless and safe to reuse.
    """

    registry = MetadataRegistry()

    registry.register(
        PDFMetadataProvider(),
    )

    registry.register(
        LanguageMetadataProvider(),
    )

    return registry


@lru_cache
def _get_metadata_service() -> MetadataEnrichmentService:
    """
    Create the metadata enrichment service.
    """

    return MetadataEnrichmentService(
        registry=_get_metadata_registry(),
    )


@lru_cache
def _get_statistics_registry() -> StatisticsRegistry:
    """
    Create the statistics provider registry.

    Provider implementations are stateless and safe to reuse.
    """

    registry = StatisticsRegistry()

    registry.register(
        PDFStatisticsProvider(),
    )

    return registry


@lru_cache
def _get_statistics_service() -> StatisticsEnrichmentService:
    """
    Create the statistics enrichment service.
    """

    return StatisticsEnrichmentService(
        registry=_get_statistics_registry(),
    )


@lru_cache
def _get_artifact_builder() -> ArtifactBuilder:
    """
    Create the artifact builder.
    """

    return ArtifactBuilder()


@lru_cache
def _get_chunking_service() -> ChunkingService:
    """
    Create the chunking service.
    """

    return create_chunking_service()


@lru_cache
def _get_chunk_artifact_builder() -> ChunkArtifactBuilder:
    """
    Create the chunk artifact builder.
    """

    return ChunkArtifactBuilder()


@lru_cache
def _get_temporary_file_manager() -> TemporaryFileManager:
    """
    Create the temporary file manager.
    """

    return TemporaryFileManager()


def get_document_repository(
    session: AsyncSession = Depends(get_db),
) -> DocumentRepository:
    """
    Create a DocumentRepository.
    """

    return DocumentRepository(session)


def get_duplicate_detection_service(
    repository: DocumentRepository = Depends(
        get_document_repository,
    ),
) -> DuplicateDetectionService:
    """
    Create the duplicate detection service.
    """

    return DuplicateDetectionService(
        repository=repository,
    )


def get_document_storage() -> DocumentStorage:
    """
    Return the configured document storage service.
    """

    return _get_storage()


def get_processing_queue() -> ProcessingQueue:
    """
    Return the configured processing queue.
    """

    return _get_processing_queue()


def get_file_hasher() -> FileHasher:
    """
    Return the configured file hasher.
    """

    return _get_hasher()


def get_processing_service(
    storage: DocumentStorage = Depends(
        get_document_storage,
    ),
) -> ProcessingService:
    """
    Create the document processing service.
    """

    return ProcessingService(
        storage=storage,
        temporary_file_manager=_get_temporary_file_manager(),
        parser_registry=_get_parser_registry(),
        metadata_service=_get_metadata_service(),
        statistics_service=_get_statistics_service(),
        artifact_builder=_get_artifact_builder(),
        artifact_writer=ArtifactWriter(storage),
        chunking_service=_get_chunking_service(),
        chunk_artifact_builder=_get_chunk_artifact_builder(),
        chunk_artifact_writer=ChunkArtifactWriter(storage),
    )


def get_document_processing_service(
    processing_service: ProcessingService = Depends(
        get_processing_service,
    ),
    repository: DocumentRepository = Depends(
        get_document_repository,
    ),
    session: AsyncSession = Depends(get_db),
) -> DocumentProcessingService:
    """
    Create the application document processing service.
    """

    return DocumentProcessingService(
        processing_service=processing_service,
        document_repository=repository,
        session=session,
    )


def get_queued_document_processing_service(
    document_processing_service: DocumentProcessingService = Depends(
        get_document_processing_service,
    ),
    repository: DocumentRepository = Depends(
        get_document_repository,
    ),
) -> QueuedDocumentProcessingService:
    """
    Create the queued document processing service.
    """

    return QueuedDocumentProcessingService(
        document_processing_service=document_processing_service,
        document_repository=repository,
    )


def get_upload_service(
    session: AsyncSession = Depends(get_db),
    repository: DocumentRepository = Depends(
        get_document_repository,
    ),
    storage: DocumentStorage = Depends(
        get_document_storage,
    ),
    hasher: FileHasher = Depends(
        get_file_hasher,
    ),
    duplicate_detection_service: DuplicateDetectionService = Depends(
        get_duplicate_detection_service,
    ),
    processing_queue: ProcessingQueue = Depends(
        get_processing_queue,
    ),
) -> UploadService:
    """
    Create the upload service.
    """

    return UploadService(
        session=session,
        repository=repository,
        storage=storage,
        hasher=hasher,
        duplicate_detection_service=duplicate_detection_service,
        processing_queue=processing_queue,
    )


def get_processing_worker(
    queue: ProcessingQueue = Depends(
        get_processing_queue,
    ),
    queued_document_processing_service: QueuedDocumentProcessingService = Depends(
        get_queued_document_processing_service,
    ),
) -> ProcessingWorker:
    """
    Create the background processing worker.
    """

    return ProcessingWorker(
        queue=queue,
        queued_document_processing_service=(queued_document_processing_service),
    )
