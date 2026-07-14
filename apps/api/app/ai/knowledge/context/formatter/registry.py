from app.ai.knowledge.context.formatter.enums import (
    PromptFormatStrategy,
)
from app.ai.knowledge.context.formatter.interfaces import (
    PromptFormatterProvider,
)


class PromptFormatterRegistry:
    def __init__(
        self,
    ) -> None:

        self._providers: dict[
            PromptFormatStrategy,
            PromptFormatterProvider,
        ] = {}

    def register(
        self,
        strategy: PromptFormatStrategy,
        provider: PromptFormatterProvider,
    ) -> None:

        self._providers[strategy] = provider

    def get(
        self,
        strategy: PromptFormatStrategy,
    ) -> PromptFormatterProvider:

        provider = self._providers.get(
            strategy,
        )

        if provider is None:
            raise ValueError(f"No formatter registered for {strategy}")

        return provider
