"""
Storage exceptions.
"""


class StorageError(Exception):
    """Base storage exception."""


class StorageUploadError(StorageError):
    """Raised when uploading fails."""


class StorageDownloadError(StorageError):
    """Raised when downloading fails."""


class StorageDeleteError(StorageError):
    """Raised when deleting fails."""


class StorageNotFoundError(StorageError):
    """Raised when an object does not exist."""


class StorageListError(StorageError):
    """Raised when listing keys under a prefix fails."""
