"""
Chunking provider interfaces.

Every chunking implementation must implement the ChunkingProvider
interface.

The Chunking Service depends only on this interface, allowing chunking
strategies to be replaced without changing application code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.ai.knowledge.chunking.enums import ChunkingStrategy
from app.ai.knowledge.chunking.models import Chunk
from app.ai.knowledge.processing.models import ProcessedDocument


class ChunkingProvider(ABC):
    """
    Base interface for every chunking provider.
    """

    @property
    @abstractmethod
    def strategy(self) -> ChunkingStrategy:
        """
        Strategy implemented by this provider.
        """

    @abstractmethod
    async def chunk(
        self,
        document: ProcessedDocument,
    ) -> list[Chunk]:
        """
        Generate retrieval-ready chunks from a processed document.

        Args:
            document:
                Canonical processed document.

        Returns:
            Ordered list of generated chunks.
        """
