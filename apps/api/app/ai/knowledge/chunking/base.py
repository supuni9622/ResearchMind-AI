"""
Base chunking provider.

Provides common functionality shared by all chunking implementations.
"""

from __future__ import annotations

from abc import ABC

from app.ai.knowledge.chunking.interfaces import ChunkingProvider


class BaseChunkingProvider(
    ChunkingProvider,
    ABC,
):
    """
    Base class for chunking providers.

    Concrete implementations inherit from this class to share common
    functionality while implementing only the chunking algorithm.
    """
