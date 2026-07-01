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

from app.ai.knowledge.processing.interfaces import ParseRequest
from app.ai.knowledge.processing.models import ProcessingResult
from app.ai.knowledge.processing.service import ProcessingService
from app.models.document import Document
from app.models.enums import DocumentProcessingStatus
from app.repositories.document import DocumentRepository


class DocumentProcessingService:
    """
    Application-level orchestration for document processing.
    """

    def __init__(
        self,
        processing_service: ProcessingService,
        document_repository: DocumentRepository,
    ) -> None:
        self._processing_service = processing_service
        self._document_repository = document_repository

    async def process(
        self,
        document: Document,
        request: ParseRequest,
    ) -> ProcessingResult:
        """
        Process a document and update its processing lifecycle.
        """

        document.processing_status = DocumentProcessingStatus.PROCESSING

        await self._document_repository.update(document)

        try:
            result = await self._processing_service.process(
                owner_id=str(document.owner_id),
                request=request,
            )

            document.processing_status = DocumentProcessingStatus.COMPLETED
            document.processed_at = datetime.now(UTC)
            document.processing_error = None

            await self._document_repository.update(document)

            return result

        except Exception as exc:
            document.processing_status = DocumentProcessingStatus.FAILED
            document.processing_error = str(exc)

            await self._document_repository.update(document)

            raise
