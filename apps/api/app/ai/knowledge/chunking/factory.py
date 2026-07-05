"""
Chunking service factory.

Assembles the Chunking Platform by registering all available chunking
providers and constructing the ChunkingService.

This module is the single composition root for the Chunking Platform.
Adding a new chunking strategy should require only registering the
provider here without modifying the rest of the application.
"""

from __future__ import annotations

from app.ai.knowledge.chunking.config import FixedChunkingConfig
from app.ai.knowledge.chunking.providers.fixed import FixedChunkingProvider
from app.ai.knowledge.chunking.registry import ChunkingRegistry
from app.ai.knowledge.chunking.service import ChunkingService


def create_chunking_service() -> ChunkingService:
    """
    Create a fully configured ChunkingService.
    """

    registry = ChunkingRegistry()

    registry.register(
        FixedChunkingProvider(
            FixedChunkingConfig(),
        )
    )

    return ChunkingService(
        registry=registry,
    )
