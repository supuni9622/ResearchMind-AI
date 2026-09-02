"""
Chat attachment validation.
"""

from __future__ import annotations

import structlog

from app.ai.runtime.chat.attachments.constants import (
    MAX_ATTACHMENT_SIZE_BYTES,
    SUPPORTED_IMAGE_CONTENT_TYPES,
    SUPPORTED_IMAGE_EXTENSIONS,
    get_extension,
)
from app.ai.runtime.chat.attachments.exceptions import (
    AttachmentTooLargeError,
    EmptyAttachmentError,
    InvalidAttachmentFilenameError,
    UnsupportedAttachmentContentTypeError,
    UnsupportedAttachmentExtensionError,
)

logger = structlog.get_logger()


class ChatAttachmentValidator:
    """Validates uploaded chat image attachments."""

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
            ChatAttachmentValidationError
        """

        if not filename.strip():
            logger.warning("chat_attachment.validation_failed", reason="empty_filename")
            raise InvalidAttachmentFilenameError("Filename cannot be empty.")

        extension = get_extension(filename)

        if extension not in SUPPORTED_IMAGE_EXTENSIONS:
            logger.warning(
                "chat_attachment.validation_failed",
                reason="unsupported_extension",
                extension=extension,
                filename=filename,
            )
            raise UnsupportedAttachmentExtensionError(
                f"Unsupported file extension: {extension}",
            )

        if content_type not in SUPPORTED_IMAGE_CONTENT_TYPES:
            logger.warning(
                "chat_attachment.validation_failed",
                reason="unsupported_content_type",
                content_type=content_type,
                filename=filename,
            )
            raise UnsupportedAttachmentContentTypeError(
                f"Unsupported content type: {content_type}",
            )

        if size_bytes <= 0:
            logger.warning(
                "chat_attachment.validation_failed",
                reason="empty_file",
                filename=filename,
            )
            raise EmptyAttachmentError("Uploaded attachment is empty.")

        if size_bytes > MAX_ATTACHMENT_SIZE_BYTES:
            logger.warning(
                "chat_attachment.validation_failed",
                reason="file_too_large",
                size_bytes=size_bytes,
                max_bytes=MAX_ATTACHMENT_SIZE_BYTES,
                filename=filename,
            )
            raise AttachmentTooLargeError(
                f"Maximum attachment size is {MAX_ATTACHMENT_SIZE_BYTES} bytes.",
            )
