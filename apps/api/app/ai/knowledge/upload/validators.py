# Validation logic - File validation
"""
Upload validation.
"""

from app.ai.knowledge.upload.constants import (
    MAX_UPLOAD_SIZE_BYTES,
    SUPPORTED_CONTENT_TYPES,
    SUPPORTED_EXTENSIONS,
    get_extension,
)
from app.ai.knowledge.upload.exceptions import (
    EmptyFileError,
    FileTooLargeError,
    InvalidFilenameError,
    UnsupportedContentTypeError,
    UnsupportedExtensionError,
)


class UploadValidator:
    """Validates uploaded documents."""

    @staticmethod
    def validate(
        *,
        filename: str,
        content_type: str,
        size_bytes: int,
    ) -> None:
        """
        Validate upload metadata.

        Raises:
            UploadValidationError
        """

        if not filename.strip():
            raise InvalidFilenameError("Filename cannot be empty.")

        extension = get_extension(filename)

        if extension not in SUPPORTED_EXTENSIONS:
            raise UnsupportedExtensionError(f"Unsupported file extension: {extension}")

        if content_type not in SUPPORTED_CONTENT_TYPES:
            raise UnsupportedContentTypeError(f"Unsupported content type: {content_type}")

        if size_bytes <= 0:
            raise EmptyFileError("Uploaded file is empty.")

        if size_bytes > MAX_UPLOAD_SIZE_BYTES:
            raise FileTooLargeError(f"Maximum upload size is {MAX_UPLOAD_SIZE_BYTES} bytes.")
