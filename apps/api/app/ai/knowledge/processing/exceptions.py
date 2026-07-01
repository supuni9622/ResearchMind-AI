"""
Exceptions for the document processing pipeline.
"""


class ProcessingError(Exception):
    """
    Base exception for all document processing errors.
    """


class ParserNotFoundError(ProcessingError):
    """
    Raised when no parser is registered for a document format.
    """


class UnsupportedDocumentFormatError(ProcessingError):
    """
    Raised when the uploaded document format is not supported.
    """


class DocumentParsingError(ProcessingError):
    """
    Raised when a parser fails to process a document.
    """


class MetadataExtractionError(ProcessingError):
    """
    Raised when metadata extraction fails.
    """
