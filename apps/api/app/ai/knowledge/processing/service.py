"""
Document processing service.

The ProcessingService orchestrates the complete document processing
pipeline.

Responsibilities:

- Download document from storage
- Create a temporary processing file
- Resolve parser
- Parse document
- Enrich metadata
- Build processing artifacts
- Persist processing artifacts
- Return the canonical processed document

Database operations, queues, workers, and document lifecycle
management are intentionally outside this service.
"""

from __future__ import annotations

import structlog

# from app.ai.knowledge.chunking.artifacts.builder import ChunkArtifactBuilder
# from app.ai.knowledge.chunking.artifacts.writer import ChunkArtifactWriter
# from app.ai.knowledge.chunking.service import ChunkingService
from app.ai.knowledge.processing.artifact_builder import ArtifactBuilder
from app.ai.knowledge.processing.artifact_writer import ArtifactWriter
from app.ai.knowledge.processing.enums import ProcessingStatus
from app.ai.knowledge.processing.exceptions import (
    ParserNotFoundError,
    ProcessingError,
)
from app.ai.knowledge.processing.interfaces import ParseRequest
from app.ai.knowledge.processing.metadata.service import (
    MetadataEnrichmentService,
)
from app.ai.knowledge.processing.models import (
    ProcessedDocument,
    ProcessingResult,
)
from app.ai.knowledge.processing.registry import ParserRegistry
from app.ai.knowledge.processing.statistics.service import (
    StatisticsEnrichmentService,
)
from app.ai.knowledge.processing.temporary_file_manager import (
    TemporaryFileManager,
)
from app.infrastructure.storage.interfaces import DocumentStorage

logger = structlog.get_logger()


class ProcessingService:
    """
    Orchestrates the document processing pipeline.
    """

    def __init__(
        self,
        *,
        storage: DocumentStorage,
        temporary_file_manager: TemporaryFileManager,
        parser_registry: ParserRegistry,
        metadata_service: MetadataEnrichmentService,
        statistics_service: StatisticsEnrichmentService,
        artifact_builder: ArtifactBuilder,
        artifact_writer: ArtifactWriter,
        # chunking_service: ChunkingService,
        # chunk_artifact_builder: ChunkArtifactBuilder,
        # chunk_artifact_writer: ChunkArtifactWriter,
    ) -> None:
        self._storage = storage
        self._temporary_file_manager = temporary_file_manager
        self._parser_registry = parser_registry
        self._metadata_service = metadata_service
        self._statistics_service = statistics_service
        self._artifact_builder = artifact_builder
        self._artifact_writer = artifact_writer
        # self._chunking_service = chunking_service
        # self._chunk_artifact_builder = chunk_artifact_builder
        # self._chunk_artifact_writer = chunk_artifact_writer

    async def process(
        self,
        *,
        owner_id: str,
        request: ParseRequest,
    ) -> ProcessingResult:
        """
        Process a document through the complete processing pipeline.
        """

        log = logger.bind(
            document_id=str(request.document_id),
            owner_id=owner_id,
            document_format=request.document_format.value,
        )

        log.info("processing.started")

        try:
            parser = self._parser_registry.get_parser(
                request.document_format,
            )

        except ParserNotFoundError:
            log.warning(
                "processing.parser_not_found",
                document_format=request.document_format.value,
            )
            raise

        log.debug(
            "processing.parser_resolved",
            parser=parser.parser_name,
        )

        try:
            document_bytes = await self._storage.download(
                key=request.storage_key,
            )

            log.debug(
                "processing.document_downloaded",
                bytes=len(document_bytes),
            )

            async with self._temporary_file_manager.create(
                content=document_bytes,
                filename=request.filename,
            ) as temp_path:
                parser_request = request.model_copy(
                    update={
                        "file_path": temp_path,
                    }
                )

                document: ProcessedDocument = await parser.parse(
                    parser_request,
                )

                # Enrich the parsed document with application-level metadata.
                document = document.model_copy(
                    update={
                        "document_id": request.document_id,
                        "filename": request.filename,
                    }
                )
                log.info(
                    "processing.document_enriched",
                    document=document.model_dump(mode="json"),
                )

                log.debug(
                    "processing.metadata_enrichment_started",
                )

                document = await self._metadata_service.enrich(
                    document=document,
                    file_path=temp_path,
                )

                log.debug(
                    "processing.metadata_enrichment_completed",
                )
                log.debug(
                    "processing.statistics_enrichment_started",
                )

                document = await self._statistics_service.enrich(
                    document=document,
                    file_path=temp_path,
                )

                log.debug(
                    "processing.statistics_enrichment_completed",
                )

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
            character_count=document.statistics.character_count,
            word_count=document.statistics.word_count,
        )

        log.debug(
            "processing.parse_completed",
            parser=parser.parser_name,
            character_count=document.statistics.character_count,
            word_count=document.statistics.word_count,
        )

        await self._persist_processing_artifacts(
            owner_id=owner_id,
            request=request,
            document=document,
            parser_name=parser.parser_name,
            log=log,
        )

        log.info("processing.completed")

        return ProcessingResult(
            status=ProcessingStatus.COMPLETED,
            document=document,
        )

    async def _persist_processing_artifacts(
        self,
        *,
        owner_id: str,
        request: ParseRequest,
        document: ProcessedDocument,
        parser_name: str,
        log: structlog.typing.FilteringBoundLogger,
    ) -> None:
        """
        Build and persist processing artifacts.

        This stage serializes the canonical processed document into the
        processing artifacts consumed by downstream AI platforms.
        """

        try:
            log.info(
                "processing.document_before_artifact_builder",
                document=document.model_dump(mode="json"),
            )

            artifacts = self._artifact_builder.build(
                document,
            )

            log.debug(
                "processing.artifacts_built",
            )

            await self._artifact_writer.write(
                owner_id=owner_id,
                document_id=str(request.document_id),
                artifacts=artifacts,
            )

        except Exception as exc:
            log.exception(
                "processing.artifact_persistence_failed",
                parser=parser_name,
                exc_type=type(exc).__name__,
            )
            raise
