"""
Memory Platform exceptions.
"""


class MemoryError(Exception):
    """Base exception for the Memory Platform."""


class MemoryNotFoundError(MemoryError):
    """Raised when a memory lookup by id finds nothing owned by the caller."""


class MemoryValidationError(MemoryError):
    """Raised when a `remember()`/`update_memory()` payload is invalid."""


class MemoryStorageError(MemoryError):
    """Raised when a storage backend (Valkey/Postgres/Qdrant) operation fails."""
