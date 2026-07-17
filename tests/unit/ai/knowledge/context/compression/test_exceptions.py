"""
Unit tests for the compression exception hierarchy.

Covers:
- CompressionProviderError and CompressionTimeoutError are both
  catchable as CompressionError -- CompressionService's fallback path
  relies on this to catch any provider failure mode.
"""

from __future__ import annotations

from app.ai.knowledge.context.compression.exceptions import (
    CompressionError,
    CompressionProviderError,
    CompressionTimeoutError,
)


def test_compression_provider_error_is_a_compression_error() -> None:
    assert issubclass(CompressionProviderError, CompressionError)


def test_compression_timeout_error_is_a_compression_error() -> None:
    assert issubclass(CompressionTimeoutError, CompressionError)
