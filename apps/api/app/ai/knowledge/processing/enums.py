"""
Processing domain enumerations.

These enums define the lifecycle and supported parser types for the
Knowledge Platform document processing pipeline.

The processing module converts uploaded documents into a normalized
representation suitable for chunking, embeddings, retrieval, and
future AI workflows.
"""

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
