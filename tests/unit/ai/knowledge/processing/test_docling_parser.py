from pathlib import Path
from uuid import uuid4

import pytest
from app.ai.knowledge.processing.enums import DocumentFormat
from app.ai.knowledge.processing.interfaces import ParseRequest
from app.ai.knowledge.processing.parsers.docling import DoclingParser
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from PIL import Image, ImageDraw, ImageFont


def test_docling_parser_supports_image_format():
    """Image-to-RAG ingestion (Wave 4, docs/PRIORITIZED_ROADMAP.md) --
    `ParserRegistry` auto-registers a parser for every format in this
    set, so this is what actually routes an uploaded image here."""

    parser = DoclingParser()

    assert DocumentFormat.IMAGE in parser.supported_formats


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


@pytest.mark.asyncio
async def test_docling_parser_image_ocr(tmp_path: Path):
    """
    Image-to-RAG ingestion (Wave 4, docs/PRIORITIZED_ROADMAP.md) --
    proves OCR text actually comes back from a standalone image, not
    just that `DocumentFormat.IMAGE` is accepted. Generated at test
    time (Pillow is already a Docling dependency) rather than a
    committed binary fixture like `tests/fixtures/sample.pdf`.
    """

    image = Image.new("RGB", (600, 200), color="white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 60), "RESEARCHMIND", fill="black", font=ImageFont.load_default(size=48))

    png_path = tmp_path / "sample.png"
    image.save(png_path)

    parser = DoclingParser()

    request = ParseRequest(
        document_id=uuid4(),
        storage_key="tests/fixtures/sample.png",
        filename="sample.png",
        content_type="image/png",
        file_path=png_path,
        document_format=DocumentFormat.IMAGE,
    )

    result = await parser.parse(request)

    assert "RESEARCHMIND" in result.raw_text.upper()
    assert result.format == DocumentFormat.IMAGE
