"""
Document processing service.

The ProcessingService orchestrates the complete document processing
pipeline.

Responsibilities:

- Resolve parser
- Parse document
- Build processing artifacts
- Persist processing artifacts
- Return the canonical processed document

Infrastructure concerns (storage) are delegated to the ArtifactWriter.
Parsing concerns are delegated to parser implementations.
"""

from __future__ import annotations

import structlog

from app.ai.knowledge.processing.artifact_builder import ArtifactBuilder
from app.ai.knowledge.processing.artifact_writer import ArtifactWriter
from app.ai.knowledge.processing.enums import ProcessingStatus
from app.ai.knowledge.processing.exceptions import ParserNotFoundError, ProcessingError
from app.ai.knowledge.processing.interfaces import ParseRequest
from app.ai.knowledge.processing.models import (
    ProcessedDocument,
    ProcessingResult,
)
from app.ai.knowledge.processing.registry import ParserRegistry

logger = structlog.get_logger()


class ProcessingService:
    """
    Orchestrates document processing.

    Responsibilities:

    - Resolve parser
    - Execute parser
    - Build and persist artifacts
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
        artifact_builder: ArtifactBuilder,
        artifact_writer: ArtifactWriter,
    ) -> None:
        self._parser_registry = parser_registry
        self._artifact_builder = artifact_builder
        self._artifact_writer = artifact_writer

    async def process(
        self,
        *,
        owner_id: str,
        request: ParseRequest,
    ) -> ProcessingResult:
        """
        Process a document through the full pipeline.

        Flow:

            Parser
                ↓
            ProcessedDocument
                ↓
            ArtifactBuilder
                ↓
            ArtifactWriter
                ↓
            ProcessingResult
        """

        log = logger.bind(
            document_id=str(request.document_id),
            document_format=request.document_format.value,
            owner_id=owner_id,
        )

        log.info("processing.started")

        try:
            parser = self._parser_registry.get_parser(request.document_format)
        except ParserNotFoundError:
            log.warning(
                "processing.parser_not_found",
                document_format=request.document_format.value,
            )
            raise

        log.debug("processing.parser_resolved", parser=parser.parser_name)

        try:
            document: ProcessedDocument = await parser.parse(request)
        except ProcessingError:
            raise
        except Exception as exc:
            log.exception(
                "processing.parse_failed",
                parser=parser.parser_name,
                exc_type=type(exc).__name__,
            )
            raise

        log.debug(
            "processing.parse_completed",
            parser=parser.parser_name,
            char_count=document.statistics.character_count,
            word_count=document.statistics.word_count,
        )

        log.debug("processing.artifacts.building")
        artifacts = self._artifact_builder.build(document)

        log.debug("processing.artifacts.writing")
        try:
            await self._artifact_writer.write(
                owner_id=owner_id,
                document_id=str(request.document_id),
                artifacts=artifacts,
            )
        except Exception as exc:
            log.exception(
                "processing.artifacts.write_failed",
                exc_type=type(exc).__name__,
            )
            raise

        log.info("processing.completed")

        return ProcessingResult(
            status=ProcessingStatus.COMPLETED,
            document=document,
        )
