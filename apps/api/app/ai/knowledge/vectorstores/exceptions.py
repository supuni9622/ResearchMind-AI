"""
Vector Store Platform exceptions.
"""

from __future__ import annotations


class VectorStoreError(Exception):
    """
    Base exception for the Vector Store Platform.
    """


class VectorStoreProviderNotFoundError(VectorStoreError):
    """
    Raised when a requested vector store provider is not registered.
    """


class CollectionAlreadyExistsError(VectorStoreError):
    """
    Raised when attempting to create a collection that already exists.
    """


class CollectionNotFoundError(VectorStoreError):
    """
    Raised when a requested collection does not exist.
    """


class VectorStoreValidationError(VectorStoreError):
    """
    Raised when vector store input validation fails.
    """


class VectorIndexingError(VectorStoreError):
    """
    Raised when vectors cannot be indexed.
    """


class VectorDeletionError(VectorStoreError):
    """
    Raised when indexed vectors cannot be deleted.
    """


class CollectionOperationError(VectorStoreError):
    """
    Raised when a collection operation fails.

    Examples include:

    - create collection
    - delete collection
    - update collection
    - collection information retrieval
    """
