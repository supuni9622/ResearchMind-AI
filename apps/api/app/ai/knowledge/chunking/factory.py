"""
Chunking service factory.

Assembles the Chunking Platform by registering all available chunking
providers and constructing the ChunkingService.

This module is the single composition root for the Chunking Platform.
Adding a new chunking strategy should require only registering the
provider here without modifying the rest of the application.
"""

from __future__ import annotations

from app.ai.knowledge.chunking.config import (
    FixedChunkingConfig,
    HierarchicalChunkingConfig,
    MarkdownChunkingConfig,
    RecursiveChunkingConfig,
)
from app.ai.knowledge.chunking.interfaces import ChunkingProvider
from app.ai.knowledge.chunking.providers.fixed import FixedChunkingProvider
from app.ai.knowledge.chunking.providers.hierarchical import (
    HierarchicalChunkingProvider,
)
from app.ai.knowledge.chunking.providers.markdown import MarkdownChunkingProvider
from app.ai.knowledge.chunking.providers.recursive import (
    RecursiveChunkingProvider,
)
from app.ai.knowledge.chunking.registry import ChunkingRegistry
from app.ai.knowledge.chunking.service import ChunkingService


def create_chunking_registry() -> ChunkingRegistry:
    """
    Create a fully configured ChunkingRegistry.

    This is the single place where chunking providers are constructed and
    registered. Both `create_chunking_service()` and the Benchmark Platform
    depend on this function rather than duplicating provider construction.
    """

    registry = ChunkingRegistry()

    providers: list[ChunkingProvider] = [
        FixedChunkingProvider(
            FixedChunkingConfig(),
        ),
        RecursiveChunkingProvider(
            RecursiveChunkingConfig(),
        ),
        MarkdownChunkingProvider(
            MarkdownChunkingConfig(),
        ),
        HierarchicalChunkingProvider(
            HierarchicalChunkingConfig(),
        ),
    ]

    for provider in providers:
        registry.register(provider)

    return registry


def create_chunking_service() -> ChunkingService:
    """
    Create a fully configured ChunkingService.
    """

    return ChunkingService(
        registry=create_chunking_registry(),
    )
