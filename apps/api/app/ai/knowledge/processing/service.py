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

from app.ai.knowledge.processing.artifact_builder import ArtifactBuilder
from app.ai.knowledge.processing.artifact_writer import ArtifactWriter
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
        Process a document.

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

        parser = self._parser_registry.get_parser(
            request.document_format,
        )

        document: ProcessedDocument = await parser.parse(
            request,
        )

        artifacts = self._artifact_builder.build(
            document,
        )

        await self._artifact_writer.write(
            owner_id=owner_id,
            document_id=str(request.document_id),
            artifacts=artifacts,
        )

        return ProcessingResult(
            status=ProcessingStatus.COMPLETED,
            document=document,
        )
