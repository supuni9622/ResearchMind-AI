# Upload exceptions - Upload-specific exceptions
"""
Upload validation exceptions.
"""


class UploadValidationError(Exception):
    """Base upload validation exception."""


class EmptyFileError(UploadValidationError):
    """Raised when an uploaded file is empty."""


class FileTooLargeError(UploadValidationError):
    """Raised when an uploaded file exceeds the maximum size."""


class UnsupportedContentTypeError(UploadValidationError):
    """Raised when the MIME type is not supported."""


class UnsupportedExtensionError(UploadValidationError):
    """Raised when the file extension is not supported."""


class InvalidFilenameError(UploadValidationError):
    """Raised when the filename is invalid."""
