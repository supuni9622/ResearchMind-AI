from abc import (
    ABC,
    abstractmethod,
)

from app.ai.knowledge.context.formatter.models import (
    PromptFormattingResult,
)
from app.ai.knowledge.context.models import (
    PromptContext,
)


class PromptFormatterProvider(
    ABC,
):
    @abstractmethod
    async def format(
        self,
        context: PromptContext,
    ) -> PromptFormattingResult:
        pass
