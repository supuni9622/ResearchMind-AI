"""
Chunking service.

The ChunkingService orchestrates the chunk generation workflow.

It is responsible for:

- validating inputs
- resolving the requested chunking provider
- delegating chunk generation
- returning the generated chunks

The service contains no chunking algorithm itself.

Concrete chunking logic lives entirely inside provider implementations.
"""

from __future__ import annotations

from app.ai.knowledge.chunking.enums import ChunkingStrategy
from app.ai.knowledge.chunking.exceptions import ChunkingValidationError
from app.ai.knowledge.chunking.models import Chunk
from app.ai.knowledge.chunking.registry import ChunkingRegistry
from app.ai.knowledge.processing.models import ProcessedDocument


class ChunkingService:
    """
    Orchestrates document chunk generation.

    The service is intentionally lightweight and depends only on the
    ChunkingRegistry. This keeps the orchestration layer independent
    from concrete chunking implementations.
    """

    def __init__(
        self,
        registry: ChunkingRegistry,
    ) -> None:
        self._registry = registry

    async def chunk(
        self,
        document: ProcessedDocument,
        strategy: ChunkingStrategy,
    ) -> list[Chunk]:
        """
        Generate chunks using the requested strategy.

        Args:
            document:
                Canonical processed document.

            strategy:
                Chunking strategy to use.

        Returns:
            Ordered list of generated chunks.
        """

        self._validate(document)

        provider = self._registry.get(strategy)

        return await provider.chunk(document)

    @staticmethod
    def _validate(
        document: ProcessedDocument,
    ) -> None:
        """
        Validate the processed document before chunking.
        """

        if not document.raw_text.strip():
            raise ChunkingValidationError(
                "Processed document contains no text.",
            )
