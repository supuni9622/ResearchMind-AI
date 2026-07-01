from pathlib import Path
from uuid import uuid4

import pytest
from app.ai.knowledge.processing.enums import (
    DocumentFormat,
    ProcessingStatus,
)
from app.ai.knowledge.processing.interfaces import ParseRequest
from app.ai.knowledge.processing.parsers.docling import DoclingParser
from app.ai.knowledge.processing.registry import ParserRegistry
from app.ai.knowledge.processing.service import ProcessingService


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

    service = ProcessingService(
        parser_registry=registry,
    )

    request = ParseRequest(
        document_id=uuid4(),
        file_path=Path("tests/fixtures/sample.pdf"),
        document_format=DocumentFormat.PDF,
    )

    result = await service.process(request)

    assert result.status == ProcessingStatus.COMPLETED
    assert result.document is not None

    document = result.document

    assert document.format == DocumentFormat.PDF
    assert document.markdown != ""
    assert document.raw_text != ""

    assert document.statistics.character_count > 0
    assert document.statistics.word_count > 0

    assert document.metadata.title == "sample"
