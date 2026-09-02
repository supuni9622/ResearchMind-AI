"""
Chat attachment exceptions.
"""


class ChatAttachmentValidationError(Exception):
    """Base chat-attachment validation exception."""


class EmptyAttachmentError(ChatAttachmentValidationError):
    """Raised when an uploaded attachment is empty."""


class AttachmentTooLargeError(ChatAttachmentValidationError):
    """Raised when an uploaded attachment exceeds the maximum size."""


class UnsupportedAttachmentContentTypeError(ChatAttachmentValidationError):
    """Raised when the MIME type is not a supported image type."""


class UnsupportedAttachmentExtensionError(ChatAttachmentValidationError):
    """Raised when the file extension is not a supported image type."""


class InvalidAttachmentFilenameError(ChatAttachmentValidationError):
    """Raised when the filename is invalid."""
