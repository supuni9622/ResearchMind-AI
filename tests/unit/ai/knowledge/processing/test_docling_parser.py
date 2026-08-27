from pathlib import Path
from uuid import uuid4

import pytest
from app.ai.knowledge.processing.enums import DocumentFormat
from app.ai.knowledge.processing.interfaces import ParseRequest
from app.ai.knowledge.processing.parsers.docling import DoclingParser
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions


def test_docling_parser_enables_ocr_for_scanned_pages():
    """Regression: OCR was off (`do_ocr=False`), so a scanned/image-only
    PDF page had no extractable text layer and silently parsed to
    near-empty content instead of erroring -- invisible to retrieval
    with no signal anything was wrong."""

    parser = DoclingParser()

    pipeline_options = parser._converter.format_to_options[InputFormat.PDF].pipeline_options

    assert isinstance(pipeline_options, PdfPipelineOptions)
    assert pipeline_options.do_ocr is True


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
