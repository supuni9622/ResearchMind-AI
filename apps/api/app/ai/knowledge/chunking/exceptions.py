"""
Chunking domain exceptions.
"""

from __future__ import annotations


class ChunkingError(Exception):
    """
    Base exception for the Chunking Platform.
    """


class ChunkingProviderNotFoundError(ChunkingError):
    """
    Raised when a chunking provider cannot be resolved.
    """


class ChunkingValidationError(ChunkingError):
    """
    Raised when a processed document cannot be chunked.
    """
