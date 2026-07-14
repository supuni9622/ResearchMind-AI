from app.ai.knowledge.context.guardrails.enums import (
    GuardrailStrategy,
)
from app.ai.knowledge.context.guardrails.providers.rule_based import (
    RuleBasedGuardrailProvider,
)
from app.ai.knowledge.context.guardrails.registry import (
    GuardrailRegistry,
)
from app.ai.knowledge.context.guardrails.service import (
    ContextGuardrailService,
)


def create_context_guardrail_service() -> ContextGuardrailService:

    registry = GuardrailRegistry()

    registry.register(
        GuardrailStrategy.RULE_BASED,
        RuleBasedGuardrailProvider(),
    )

    return ContextGuardrailService(
        registry=registry,
    )
