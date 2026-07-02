"""
Responsibilities:
1. Update status → PROCESSING
2. Invoke ProcessingService
3. Update status → COMPLETED
4. On exception → FAILED
5. Store processing error

Application service for document processing.

This service orchestrates the complete document processing workflow.

Responsibilities:

- Update document processing status
- Invoke the AI processing pipeline
- Handle processing failures
- Persist processing state

The actual AI processing is delegated to ProcessingService.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.knowledge.processing.interfaces import ParseRequest
from app.ai.knowledge.processing.models import ProcessingResult
from app.ai.knowledge.processing.service import ProcessingService
from app.models.document import Document
from app.models.enums import DocumentProcessingStatus
from app.repositories.document import DocumentRepository

logger = structlog.get_logger()

# Keeps a single runaway error message from bloating the documents table.
MAX_PROCESSING_ERROR_LENGTH = 2000


class DocumentProcessingService:
    """
    Application-level orchestration for document processing.
    """

    def __init__(
        self,
        processing_service: ProcessingService,
        document_repository: DocumentRepository,
        session: AsyncSession,
    ) -> None:
        self._processing_service = processing_service
        self._document_repository = document_repository
        self._session = session

    async def process(
        self,
        document: Document,
        request: ParseRequest,
    ) -> ProcessingResult:
        """
        Process a document and update its processing lifecycle.
        """

        log = logger.bind(
            document_id=str(document.id),
            owner_id=str(document.owner_id),
            filename=document.filename,
            document_format=request.document_format.value,
        )

        log.info("document_processing.started")

        document.processing_status = DocumentProcessingStatus.PROCESSING

        try:
            await self._document_repository.update(document)
            await self._session.commit()
        except Exception:
            log.exception(
                "document_processing.status_update_failed",
                status=DocumentProcessingStatus.PROCESSING,
            )
            await self._session.rollback()
            raise

        log.debug("document_processing.status_updated", status=DocumentProcessingStatus.PROCESSING)

        try:
            result = await self._processing_service.process(
                owner_id=str(document.owner_id),
                request=request,
            )

            document.processing_status = DocumentProcessingStatus.COMPLETED
            document.processed_at = datetime.now(UTC)
            document.processing_error = None

            await self._document_repository.update(document)
            await self._session.commit()

            processed_at = document.processed_at
            log.info(
                "document_processing.completed",
                status=DocumentProcessingStatus.COMPLETED,
                processed_at=processed_at.isoformat() if processed_at is not None else None,
            )

            return result

        except Exception as exc:
            log.exception(
                "document_processing.failed",
                status=DocumentProcessingStatus.FAILED,
                exc_type=type(exc).__name__,
                error=str(exc),
            )

            document.processing_status = DocumentProcessingStatus.FAILED
            document.processing_error = str(exc)[:MAX_PROCESSING_ERROR_LENGTH]

            try:
                await self._document_repository.update(document)
                await self._session.commit()
            except Exception:
                log.exception("document_processing.failed_status_persist_failed")
                await self._session.rollback()

            # Always surface the original processing failure, even if we
            # could not persist the FAILED status above.
            raise
