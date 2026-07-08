"""
Indexing Platform exceptions.

These exceptions represent platform-level failures that occur while
orchestrating one or more indexing technologies.

Provider-specific exceptions (Qdrant, BM25, etc.) should be translated
into these canonical exceptions before leaving the provider layer.
"""

from __future__ import annotations


class IndexingError(Exception):
    """
    Base exception for all Indexing Platform errors.
    """


class InvalidIndexingRequestError(IndexingError):
    """
    Raised when an indexing request is invalid.
    """


class IndexingExecutionError(IndexingError):
    """
    Raised when the indexing process fails.
    """


class IndexNotSupportedError(IndexingError):
    """
    Raised when an unsupported index type is requested.
    """


class IndexAlreadyExistsError(IndexingError):
    """
    Raised when attempting to create an index that already exists.
    """


class IndexNotFoundError(IndexingError):
    """
    Raised when an expected index cannot be found.
    """


class IndexProviderError(IndexingError):
    """
    Raised when an indexing provider reports an error.

    Provider-specific exceptions should be wrapped in this exception
    before propagating outside the provider implementation.
    """


class IndexArtifactError(IndexingError):
    """
    Raised when an indexing artifact cannot be created or persisted.
    """
