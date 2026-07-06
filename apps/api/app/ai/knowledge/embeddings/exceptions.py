"""
Embedding domain exceptions.
"""

from __future__ import annotations


class EmbeddingError(Exception):
    """
    Base exception for the Embedding Platform.
    """


class EmbeddingProviderNotFoundError(EmbeddingError):
    """
    Raised when an embedding provider cannot be resolved.
    """


class EmbeddingValidationError(EmbeddingError):
    """
    Raised when embeddings cannot be generated from the provided input.
    """


class EmbeddingGenerationError(EmbeddingError):
    """
    Raised when an embedding provider fails to generate embeddings.
    """
