"""
Upload validation.
"""

from __future__ import annotations

import structlog

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

logger = structlog.get_logger()


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
            logger.warning("upload.validation_failed", reason="empty_filename")
            raise InvalidFilenameError("Filename cannot be empty.")

        extension = get_extension(filename)

        if extension not in SUPPORTED_EXTENSIONS:
            logger.warning(
                "upload.validation_failed",
                reason="unsupported_extension",
                extension=extension,
                filename=filename,
            )
            raise UnsupportedExtensionError(f"Unsupported file extension: {extension}")

        if content_type not in SUPPORTED_CONTENT_TYPES:
            logger.warning(
                "upload.validation_failed",
                reason="unsupported_content_type",
                content_type=content_type,
                filename=filename,
            )
            raise UnsupportedContentTypeError(f"Unsupported content type: {content_type}")

        if size_bytes <= 0:
            logger.warning(
                "upload.validation_failed",
                reason="empty_file",
                filename=filename,
            )
            raise EmptyFileError("Uploaded file is empty.")

        if size_bytes > MAX_UPLOAD_SIZE_BYTES:
            logger.warning(
                "upload.validation_failed",
                reason="file_too_large",
                size_bytes=size_bytes,
                max_bytes=MAX_UPLOAD_SIZE_BYTES,
                filename=filename,
            )
            raise FileTooLargeError(f"Maximum upload size is {MAX_UPLOAD_SIZE_BYTES} bytes.")
