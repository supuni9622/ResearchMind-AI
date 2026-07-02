"""
Exceptions raised by the duplicate detection module.
"""

from __future__ import annotations


class DuplicateDetectionError(Exception):
    """
    Base exception for duplicate detection.
    """


class DuplicateHashingError(DuplicateDetectionError):
    """
    Raised when a file hash cannot be computed.
    """
