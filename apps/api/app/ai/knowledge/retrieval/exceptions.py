"""
Retrieval Platform exceptions.
"""

from __future__ import annotations


class RetrievalError(Exception):
    """
    Base retrieval exception.
    """


class RetrievalProviderNotFoundError(RetrievalError):
    """
    Raised when a provider cannot be resolved.
    """


class RetrievalValidationError(RetrievalError):
    """
    Raised when retrieval inputs are invalid.
    """


class RetrievalExecutionError(RetrievalError):
    """
    Raised when retrieval execution fails.
    """
