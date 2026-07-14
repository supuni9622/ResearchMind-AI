from abc import (
    ABC,
    abstractmethod,
)

from app.ai.knowledge.context.guardrails.models import (
    GuardrailResult,
)
from app.ai.knowledge.context.models import (
    ContextChunk,
)


class GuardrailProvider(
    ABC,
):
    @abstractmethod
    async def validate(
        self,
        chunks: list[ContextChunk],
    ) -> GuardrailResult:
        pass
