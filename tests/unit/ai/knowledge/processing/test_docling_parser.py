from pathlib import Path
from uuid import uuid4

import pytest
from app.ai.knowledge.processing.enums import DocumentFormat
from app.ai.knowledge.processing.interfaces import ParseRequest
from app.ai.knowledge.processing.parsers.docling import DoclingParser


@pytest.mark.asyncio
async def test_docling_parser_pdf():
    """
    Verify Docling can parse a PDF into a ProcessedDocument.
    """

    parser = DoclingParser()

    pdf = Path("tests/fixtures/sample.pdf")

    request = ParseRequest(
        document_id=uuid4(),
        storage_key="tests/fixtures/sample.pdf",
        filename="sample.pdf",
        content_type="application/pdf",
        file_path=pdf,
        document_format=DocumentFormat.PDF,
    )

    result = await parser.parse(request)

    assert result.markdown != ""
    assert result.raw_text != ""

    assert result.metadata is not None
    assert result.statistics.character_count > 0
    assert result.statistics.word_count > 0

    assert result.format == DocumentFormat.PDF
