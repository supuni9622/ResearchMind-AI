from app.ai.knowledge.context.compression.enums import (
    CompressionStrategy,
)
from app.ai.knowledge.context.compression.models import (
    CompressionRequest,
    CompressionResult,
)
from app.ai.knowledge.context.compression.registry import (
    CompressionRegistry,
)


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

        provider = self._registry.get(strategy)

        return await provider.compress(request)
