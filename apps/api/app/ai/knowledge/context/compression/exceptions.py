"""
Compression domain exceptions.
"""

from __future__ import annotations


class CompressionError(Exception):
    """
    Base exception for the Context Compression Platform.
    """


class CompressionProviderError(CompressionError):
    """
    Raised when a compression provider fails to compress the given chunks.
    """


class CompressionTimeoutError(CompressionError):
    """
    Raised when a compression provider exceeds its allotted time budget.
    """
