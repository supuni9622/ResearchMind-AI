from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.ai.knowledge.processing.artifact_builder import ArtifactBuilder
from app.ai.knowledge.processing.enums import (
    DocumentFormat,
    ProcessingStatus,
)
from app.ai.knowledge.processing.interfaces import ParseRequest
from app.ai.knowledge.processing.parsers.docling import DoclingParser
from app.ai.knowledge.processing.registry import ParserRegistry
from app.ai.knowledge.processing.service import ProcessingService
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

    storage = AsyncMock()
    storage.download = AsyncMock(
        return_value=Path("tests/fixtures/sample.pdf").read_bytes(),
    )

    service = ProcessingService(
        storage=storage,
        temporary_file_manager=TemporaryFileManager(),
        parser_registry=registry,
        artifact_builder=ArtifactBuilder(),
        artifact_writer=writer,
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

    assert document.metadata.title == "sample"
