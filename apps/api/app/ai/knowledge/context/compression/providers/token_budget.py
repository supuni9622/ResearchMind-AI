from __future__ import annotations

from app.ai.knowledge.context.compression.enums import (
    CompressionStrategy,
)
from app.ai.knowledge.context.compression.interfaces import (
    CompressionProvider,
)
from app.ai.knowledge.context.compression.models import (
    CompressionRequest,
    CompressionResult,
    CompressionStatistics,
)


class TokenBudgetCompressionProvider(
    CompressionProvider,
):
    DEFAULT_MAX_TOKENS = 6000

    async def compress(
        self,
        request: CompressionRequest,
    ) -> CompressionResult:

        budget = request.max_tokens or self.DEFAULT_MAX_TOKENS

        chunks = sorted(
            request.chunks,
            key=lambda c: c.score,
            reverse=True,
        )

        selected = []

        current_tokens = 0

        for chunk in chunks:
            estimated = len(chunk.content) // 4

            if current_tokens + estimated > budget:
                continue

            selected.append(chunk)

            current_tokens += estimated

        return CompressionResult(
            strategy=(CompressionStrategy.TOKEN_BUDGET),
            chunks=selected,
            statistics=(
                CompressionStatistics(
                    original_chunks=len(request.chunks),
                    compressed_chunks=len(selected),
                    removed_chunks=(len(request.chunks) - len(selected)),
                    estimated_saved_tokens=(budget - current_tokens),
                )
            ),
        )
