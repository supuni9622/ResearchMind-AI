import pytest
from app.ai.knowledge.processing.enums import DocumentFormat


class TestFromContentType:
    @pytest.mark.parametrize(
        ("content_type", "expected"),
        [
            ("application/pdf", DocumentFormat.PDF),
            (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                DocumentFormat.DOCX,
            ),
            ("text/markdown", DocumentFormat.MARKDOWN),
            ("text/plain", DocumentFormat.TEXT),
            # Image-to-RAG ingestion (Wave 4, docs/PRIORITIZED_ROADMAP.md)
            ("image/png", DocumentFormat.IMAGE),
            ("image/jpeg", DocumentFormat.IMAGE),
            ("image/webp", DocumentFormat.IMAGE),
            ("image/gif", DocumentFormat.IMAGE),
        ],
    )
    def test_known_content_type_resolves(
        self,
        content_type: str,
        expected: DocumentFormat,
    ) -> None:
        assert DocumentFormat.from_content_type(content_type) == expected

    def test_unknown_content_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported content type"):
            DocumentFormat.from_content_type("application/octet-stream")
