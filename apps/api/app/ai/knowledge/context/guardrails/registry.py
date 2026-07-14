from app.ai.knowledge.context.guardrails.enums import (
    GuardrailStrategy,
)
from app.ai.knowledge.context.guardrails.interfaces import (
    GuardrailProvider,
)


class GuardrailRegistry:
    def __init__(
        self,
    ) -> None:

        self._providers: dict[
            GuardrailStrategy,
            GuardrailProvider,
        ] = {}

    def register(
        self,
        strategy: GuardrailStrategy,
        provider: GuardrailProvider,
    ) -> None:

        self._providers[strategy] = provider

    def get(
        self,
        strategy: GuardrailStrategy,
    ) -> GuardrailProvider:

        provider = self._providers.get(
            strategy,
        )

        if provider is None:
            raise ValueError(f"No guardrail provider registered for {strategy}")

        return provider
