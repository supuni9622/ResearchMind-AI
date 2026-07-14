from app.ai.knowledge.context.compression.enums import (
    CompressionStrategy,
)
from app.ai.knowledge.context.compression.interfaces import (
    CompressionProvider,
)


class CompressionRegistry:
    def __init__(
        self,
    ) -> None:

        self._providers: dict[
            CompressionStrategy,
            CompressionProvider,
        ] = {}

    def register(
        self,
        strategy: CompressionStrategy,
        provider: CompressionProvider,
    ) -> None:

        self._providers[strategy] = provider

    def get(
        self,
        strategy: CompressionStrategy,
    ) -> CompressionProvider:

        provider = self._providers.get(strategy)

        if provider is None:
            raise ValueError(f"No provider registered for {strategy}")

        return provider
