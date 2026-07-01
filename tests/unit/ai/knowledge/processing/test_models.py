"""
Unit tests for the canonical document models.

Covers:
- Construction and default values for every model class
- Discriminated union round-trip (serialize → deserialize resolves correct subclass)
- ProcessedDocument block filter properties
- extra="forbid" / extra="allow" field policies
"""

from __future__ import annotations

import pytest
from app.ai.knowledge.processing.enums import DocumentFormat, ParserType, ProcessingStatus
from app.ai.knowledge.processing.models import (
    CodeBlock,
    DocumentMetadata,
    DocumentStatistics,
    FigureBlock,
    HeadingBlock,
    ListBlock,
    ParagraphBlock,
    ProcessedDocument,
    ProcessingResult,
    ReferenceBlock,
    TableBlock,
)
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_processed_document(**overrides) -> ProcessedDocument:
    defaults = dict(
        format=DocumentFormat.PDF,
        parser=ParserType.DOCLING,
        metadata=DocumentMetadata(),
        statistics=DocumentStatistics(),
        raw_text="",
        markdown="",
        blocks=[],
    )
    defaults.update(overrides)
    return ProcessedDocument(**defaults)


# ---------------------------------------------------------------------------
# DocumentMetadata
# ---------------------------------------------------------------------------


class TestDocumentMetadata:
    def test_all_fields_optional(self) -> None:
        meta = DocumentMetadata()
        assert meta.title is None
        assert meta.author is None
        assert meta.language is None
        assert meta.source is None
        assert meta.created_at is None
        assert meta.modified_at is None
        assert meta.additional_metadata == {}

    def test_explicit_values_stored(self) -> None:
        meta = DocumentMetadata(title="Research Paper", author="Alice", language="en")
        assert meta.title == "Research Paper"
        assert meta.author == "Alice"
        assert meta.language == "en"

    def test_extra_fields_allowed(self) -> None:
        # extra="allow" — arbitrary keys are accepted
        meta = DocumentMetadata(custom_field="custom_value")
        assert meta.custom_field == "custom_value"  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# DocumentStatistics
# ---------------------------------------------------------------------------


class TestDocumentStatistics:
    def test_all_counters_default_to_zero(self) -> None:
        stats = DocumentStatistics()
        assert stats.page_count == 0
        assert stats.heading_count == 0
        assert stats.paragraph_count == 0
        assert stats.table_count == 0
        assert stats.figure_count == 0
        assert stats.code_block_count == 0
        assert stats.list_count == 0
        assert stats.reference_count == 0
        assert stats.character_count == 0
        assert stats.word_count == 0
        assert stats.line_count == 0

    def test_explicit_values_stored(self) -> None:
        stats = DocumentStatistics(page_count=5, word_count=1200)
        assert stats.page_count == 5
        assert stats.word_count == 1200


# ---------------------------------------------------------------------------
# Block types
# ---------------------------------------------------------------------------


class TestBlockTypes:
    def test_heading_block_literal(self) -> None:
        block = HeadingBlock(id="h1", page=1, text="Introduction", level=1, title="Introduction")
        assert block.block_type == "heading"
        assert block.level == 1
        assert block.title == "Introduction"

    def test_paragraph_block_literal(self) -> None:
        block = ParagraphBlock(id="p1", page=1, text="Some text.")
        assert block.block_type == "paragraph"

    def test_table_block_literal(self) -> None:
        block = TableBlock(id="t1", page=2, text="", markdown="| A | B |", caption="Table 1")
        assert block.block_type == "table"
        assert block.markdown == "| A | B |"
        assert block.caption == "Table 1"

    def test_table_block_caption_optional(self) -> None:
        block = TableBlock(id="t2", page=2, text="", markdown="| A |")
        assert block.caption is None

    def test_figure_block_literal(self) -> None:
        block = FigureBlock(id="f1", page=3, text="", caption="Figure 1")
        assert block.block_type == "figure"

    def test_code_block_literal(self) -> None:
        block = CodeBlock(id="c1", page=1, text="print('hello')", language="python")
        assert block.block_type == "code"
        assert block.language == "python"

    def test_code_block_language_optional(self) -> None:
        block = CodeBlock(id="c2", page=1, text="")
        assert block.language is None

    def test_list_block_literal(self) -> None:
        block = ListBlock(id="l1", page=1, text="", items=["a", "b"], ordered=True)
        assert block.block_type == "list"
        assert block.ordered is True
        assert block.items == ["a", "b"]

    def test_list_block_defaults(self) -> None:
        block = ListBlock(id="l2", page=1, text="")
        assert block.ordered is False
        assert block.items == []

    def test_reference_block_literal(self) -> None:
        block = ReferenceBlock(
            id="r1",
            page=None,
            text="Smith et al. 2024",
            authors=["Smith, J."],
            title="Advances in AI",
            year=2024,
            doi="10.1234/ai.2024",
        )
        assert block.block_type == "reference"
        assert block.year == 2024
        assert block.doi == "10.1234/ai.2024"

    def test_reference_block_optional_fields(self) -> None:
        block = ReferenceBlock(id="r2", text="")
        assert block.authors == []
        assert block.title is None
        assert block.year is None
        assert block.doi is None

    def test_document_block_forbids_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            ParagraphBlock(id="p1", text="", unknown_field="oops")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# Discriminated union round-trip
# ---------------------------------------------------------------------------


class TestDiscriminatedUnionRoundTrip:
    """Pydantic deserialises raw dicts to the correct block subclass via block_type."""

    def _roundtrip(self, doc: ProcessedDocument) -> ProcessedDocument:
        return ProcessedDocument.model_validate(doc.model_dump())

    def test_heading_survives_roundtrip(self) -> None:
        doc = _make_processed_document(
            blocks=[HeadingBlock(id="h1", text="Intro", level=1, title="Intro")]
        )
        restored = self._roundtrip(doc)
        assert isinstance(restored.blocks[0], HeadingBlock)
        assert restored.blocks[0].level == 1

    def test_paragraph_survives_roundtrip(self) -> None:
        doc = _make_processed_document(blocks=[ParagraphBlock(id="p1", text="Hello")])
        restored = self._roundtrip(doc)
        assert isinstance(restored.blocks[0], ParagraphBlock)

    def test_mixed_blocks_survive_roundtrip(self) -> None:
        blocks = [
            HeadingBlock(id="h1", text="H", level=2, title="H"),
            ParagraphBlock(id="p1", text="P"),
            TableBlock(id="t1", text="", markdown="| x |"),
            FigureBlock(id="f1", text=""),
            CodeBlock(id="c1", text="x = 1"),
            ListBlock(id="l1", text="", items=["a"]),
            ReferenceBlock(id="r1", text="ref"),
        ]
        doc = _make_processed_document(blocks=blocks)
        restored = self._roundtrip(doc)

        assert isinstance(restored.blocks[0], HeadingBlock)
        assert isinstance(restored.blocks[1], ParagraphBlock)
        assert isinstance(restored.blocks[2], TableBlock)
        assert isinstance(restored.blocks[3], FigureBlock)
        assert isinstance(restored.blocks[4], CodeBlock)
        assert isinstance(restored.blocks[5], ListBlock)
        assert isinstance(restored.blocks[6], ReferenceBlock)

    def test_raw_dict_deserialized_by_discriminator(self) -> None:
        raw = {
            "format": "pdf",
            "parser": "docling",
            "metadata": {},
            "statistics": {},
            "raw_text": "",
            "markdown": "",
            "blocks": [
                {
                    "id": "h1",
                    "block_type": "heading",
                    "text": "Title",
                    "level": 1,
                    "title": "Title",
                },
                {"id": "p1", "block_type": "paragraph", "text": "Body"},
            ],
        }
        doc = ProcessedDocument.model_validate(raw)
        assert isinstance(doc.blocks[0], HeadingBlock)
        assert isinstance(doc.blocks[1], ParagraphBlock)


# ---------------------------------------------------------------------------
# ProcessedDocument property filters
# ---------------------------------------------------------------------------


class TestProcessedDocumentProperties:
    def _doc_with_mixed_blocks(self) -> ProcessedDocument:
        return _make_processed_document(
            blocks=[
                HeadingBlock(id="h1", text="H1", level=1, title="H1"),
                HeadingBlock(id="h2", text="H2", level=2, title="H2"),
                ParagraphBlock(id="p1", text="Para"),
                TableBlock(id="t1", text="", markdown="| x |"),
                FigureBlock(id="f1", text=""),
                CodeBlock(id="c1", text="pass"),
                ListBlock(id="l1", text=""),
                ReferenceBlock(id="r1", text="ref"),
            ]
        )

    def test_headings_filter(self) -> None:
        doc = self._doc_with_mixed_blocks()
        assert len(doc.headings) == 2
        assert all(isinstance(b, HeadingBlock) for b in doc.headings)

    def test_paragraphs_filter(self) -> None:
        doc = self._doc_with_mixed_blocks()
        assert len(doc.paragraphs) == 1
        assert doc.paragraphs[0].id == "p1"

    def test_tables_filter(self) -> None:
        doc = self._doc_with_mixed_blocks()
        assert len(doc.tables) == 1

    def test_figures_filter(self) -> None:
        doc = self._doc_with_mixed_blocks()
        assert len(doc.figures) == 1

    def test_code_blocks_filter(self) -> None:
        doc = self._doc_with_mixed_blocks()
        assert len(doc.code_blocks) == 1

    def test_lists_filter(self) -> None:
        doc = self._doc_with_mixed_blocks()
        assert len(doc.lists) == 1

    def test_references_filter(self) -> None:
        doc = self._doc_with_mixed_blocks()
        assert len(doc.references) == 1

    def test_empty_blocks_all_properties_empty(self) -> None:
        doc = _make_processed_document(blocks=[])
        assert doc.headings == []
        assert doc.paragraphs == []
        assert doc.tables == []
        assert doc.figures == []
        assert doc.code_blocks == []
        assert doc.lists == []
        assert doc.references == []


# ---------------------------------------------------------------------------
# ProcessingResult
# ---------------------------------------------------------------------------


class TestProcessingResult:
    def test_completed_with_document(self) -> None:
        doc = _make_processed_document()
        result = ProcessingResult(status=ProcessingStatus.COMPLETED, document=doc)
        assert result.status == ProcessingStatus.COMPLETED
        assert result.document is doc
        assert result.error is None

    def test_failed_with_error_message(self) -> None:
        result = ProcessingResult(status=ProcessingStatus.FAILED, error="Parse error")
        assert result.status == ProcessingStatus.FAILED
        assert result.document is None
        assert result.error == "Parse error"

    def test_pending_with_no_document(self) -> None:
        result = ProcessingResult(status=ProcessingStatus.PENDING)
        assert result.document is None
        assert result.error is None
