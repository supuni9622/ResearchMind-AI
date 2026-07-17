from __future__ import annotations

import structlog
from app.ai.knowledge.context.compression.enums import (
    CompressionStrategy,
)
from app.ai.knowledge.context.compression.exceptions import (
    CompressionError,
)
from app.ai.knowledge.context.compression.models import (
    CompressionRequest,
    CompressionResult,
    CompressionStatistics,
)
from app.ai.knowledge.context.compression.registry import (
    CompressionRegistry,
)

logger = structlog.get_logger()


class CompressionService:
    def __init__(
        self,
        registry: CompressionRegistry,
    ) -> None:

        self._registry = registry

    async def compress(
        self,
        *,
        strategy: CompressionStrategy,
        request: CompressionRequest,
    ) -> CompressionResult:
        """
        Resolves the provider for `strategy` and delegates to it.

        An unregistered strategy is a caller/wiring bug and propagates as
        `ValueError` (see `CompressionRegistry.get`). A registered
        provider failing mid-compression is different -- compression must
        never break generation, so that case falls back to returning the
        original, uncompressed chunks instead of raising.
        """

        provider = self._registry.get(strategy)

        try:
            return await provider.compress(request)

        except CompressionError:
            logger.warning(
                "context.compression.fallback",
                strategy=strategy.value,
                chunk_count=len(request.chunks),
            )

            return CompressionResult(
                strategy=strategy,
                chunks=request.chunks,
                statistics=CompressionStatistics(
                    original_chunks=len(request.chunks),
                    compressed_chunks=len(request.chunks),
                    removed_chunks=0,
                ),
            )
