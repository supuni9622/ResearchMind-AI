from app.ai.knowledge.context.formatter.enums import (
    PromptFormatStrategy,
)
from app.ai.knowledge.context.formatter.models import (
    PromptFormattingResult,
)
from app.ai.knowledge.context.formatter.registry import (
    PromptFormatterRegistry,
)
from app.ai.knowledge.context.models import (
    PromptContext,
)


class PromptFormatterService:
    def __init__(
        self,
        registry: PromptFormatterRegistry,
    ) -> None:

        self._registry = registry

    async def format(
        self,
        *,
        strategy: PromptFormatStrategy,
        context: PromptContext,
    ) -> PromptFormattingResult:

        provider = self._registry.get(
            strategy,
        )

        return await provider.format(
            context,
        )
