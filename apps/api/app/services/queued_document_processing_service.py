"""
Application service for processing queued document jobs.

This service bridges the queue infrastructure and the existing document
processing pipeline.

Responsibilities:

- Resolve the document from the processing job
- Build the ParseRequest
- Invoke DocumentProcessingService

The actual document processing remains delegated to
DocumentProcessingService.
"""

from __future__ import annotations

import structlog

from app.ai.knowledge.processing.enums import DocumentFormat
from app.ai.knowledge.processing.interfaces import ParseRequest
from app.infrastructure.queue.models import ProcessingJob
from app.repositories.document import DocumentRepository
from app.services.document_processing_service import (
    DocumentProcessingService,
)

logger = structlog.get_logger()


class QueuedDocumentProcessingService:
    """
    Application service responsible for processing queued jobs.
    """

    def __init__(
        self,
        *,
        document_repository: DocumentRepository,
        document_processing_service: DocumentProcessingService,
    ) -> None:
        self._document_repository = document_repository
        self._document_processing_service = document_processing_service

    async def process(
        self,
        job: ProcessingJob,
    ) -> None:
        """
        Process a queued document.
        """

        log = logger.bind(
            document_id=str(job.document_id),
            owner_id=str(job.owner_id),
        )

        log.info("queued_document_processing.started")

        document = await self._document_repository.get_by_id(
            job.document_id,
        )

        if document is None:
            raise ValueError(f"Document '{job.document_id}' was not found.")

        request = ParseRequest(
            document_id=document.id,
            filename=document.filename,
            storage_key=document.storage_key,
            file_path=None,
            content_type=document.content_type,
            document_format=DocumentFormat.from_content_type(
                document.content_type,
            ),
        )

        await self._document_processing_service.process(
            document=document,
            request=request,
        )

        log.info(
            "queued_document_processing.completed",
        )
