"""
Document processing service.

The ProcessingService orchestrates document processing by selecting the
appropriate parser and converting documents into the canonical
ProcessedDocument representation.

The service contains orchestration logic only.

Parser implementations remain responsible for document parsing.
"""

from __future__ import annotations

from app.ai.knowledge.processing.enums import ProcessingStatus
from app.ai.knowledge.processing.interfaces import ParseRequest
from app.ai.knowledge.processing.models import (
    ProcessedDocument,
    ProcessingResult,
)
from app.ai.knowledge.processing.registry import ParserRegistry


class ProcessingService:
    """
    Orchestrates document processing.

    Responsibilities:

    - Resolve parser
    - Execute parser
    - Return canonical document

    Responsibilities intentionally excluded:

    - S3 download
    - Database
    - Queue
    - Worker
    """

    def __init__(
        self,
        parser_registry: ParserRegistry,
    ) -> None:
        self._parser_registry = parser_registry

    async def process(
        self,
        request: ParseRequest,
    ) -> ProcessingResult:
        """
        Process a document.

        Args:
            request:
                Processing request.

        Returns:
            ProcessingResult
        """

        parser = self._parser_registry.get_parser(request.document_format)

        document: ProcessedDocument = await parser.parse(request)

        return ProcessingResult(
            status=ProcessingStatus.COMPLETED,
            document=document,
        )
