from abc import ABC, abstractmethod

from app.ai.knowledge.context.compression.models import (
    CompressionRequest,
    CompressionResult,
)


class CompressionProvider(
    ABC,
):
    @abstractmethod
    async def compress(
        self,
        request: CompressionRequest,
    ) -> CompressionResult:
        pass
