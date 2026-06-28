"""
Document domain exceptions.
"""

from app.exceptions.base import (
    ConflictException,
    NotFoundException,
    ValidationException,
)


class DocumentUploadException(ValidationException):
    """
    Raised when a document upload fails.
    """

    def __init__(
        self,
        message: str = "Document upload failed.",
    ) -> None:
        super().__init__(message)


class DocumentNotFoundException(NotFoundException):
    """
    Raised when a document cannot be found.
    """

    def __init__(
        self,
        message: str = "Document not found.",
    ) -> None:
        super().__init__(message)


class DuplicateDocumentException(ConflictException):
    """
    Raised when a duplicate document is detected.
    """

    def __init__(
        self,
        message: str = "Document already exists.",
    ) -> None:
        super().__init__(message)
