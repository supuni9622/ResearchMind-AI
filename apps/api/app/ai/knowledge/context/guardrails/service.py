from app.ai.knowledge.context.guardrails.enums import (
    GuardrailStrategy,
)
from app.ai.knowledge.context.guardrails.models import (
    GuardrailResult,
)
from app.ai.knowledge.context.guardrails.registry import (
    GuardrailRegistry,
)
from app.ai.knowledge.context.models import (
    ContextChunk,
)


class ContextGuardrailService:
    def __init__(
        self,
        registry: GuardrailRegistry,
    ) -> None:

        self._registry = registry

    async def validate(
        self,
        *,
        strategy: GuardrailStrategy,
        chunks: list[ContextChunk],
    ) -> GuardrailResult:

        provider = self._registry.get(
            strategy,
        )

        return await provider.validate(
            chunks,
        )
