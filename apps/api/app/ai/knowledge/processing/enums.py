"""
Processing domain enumerations.

These enums define the lifecycle and supported parser types for the
Knowledge Platform document processing pipeline.

The processing module converts uploaded documents into a normalized
representation suitable for chunking, embeddings, retrieval, and
future AI workflows.
"""

from __future__ import annotations

from enum import StrEnum


class ProcessingStatus(StrEnum):
    """
    Lifecycle status of a document processing job.
    """

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ParserType(StrEnum):
    """
    Supported parser implementations.

    These values identify parser implementations registered in the
    ParserRegistry.

    They are intentionally implementation identifiers rather than
    document formats.
    """

    DOCLING = "docling"


class DocumentFormat(StrEnum):
    """
    Supported document formats.

    The format is detected before selecting a parser.
    """

    PDF = "pdf"
    DOCX = "docx"
    MARKDOWN = "markdown"
    TEXT = "text"

    @classmethod
    def from_content_type(cls, content_type: str) -> DocumentFormat:
        """
        Resolve a document format from a MIME content type.

        Raises:
            ValueError: If the content type has no known format mapping.
        """

        mapping = {
            "application/pdf": cls.PDF,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": cls.DOCX,
            "text/markdown": cls.MARKDOWN,
            "text/plain": cls.TEXT,
        }

        try:
            return mapping[content_type]
        except KeyError:
            raise ValueError(
                f"Unsupported content type: {content_type}",
            ) from None


class ProcessingStage(StrEnum):
    """
    High-level processing stages.

    These stages are useful for structured logging, tracing,
    observability, and future progress reporting.
    """

    DOWNLOAD = "download"
    DETECT_FORMAT = "detect_format"
    PARSE = "parse"
    EXTRACT_METADATA = "extract_metadata"
    NORMALIZE = "normalize"
    COMPLETE = "complete"
