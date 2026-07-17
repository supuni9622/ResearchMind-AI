from __future__ import annotations

from functools import lru_cache

import structlog
from app.ai.runtime.generation.validation.input.context_validation import (
    ContextValidator,
)
from app.ai.runtime.generation.validation.input.empty_prompt import (
    EmptyPromptValidator,
)
from app.ai.runtime.generation.validation.input.provider_limits import (
    ProviderLimitsValidator,
)
from app.ai.runtime.generation.validation.input.token_budget import (
    TokenBudgetValidator,
)
from app.ai.runtime.generation.validation.output.citation_validator import (
    CitationValidator,
)
from app.ai.runtime.generation.validation.output.hallucination_validator import (
    HallucinationValidator,
)
from app.ai.runtime.generation.validation.output.json_validator import (
    JsonValidator,
)
from app.ai.runtime.generation.validation.output.schema_validator import (
    SchemaValidator,
)
from app.ai.runtime.generation.validation.registry import (
    ValidationRegistry,
)
from app.ai.runtime.generation.validation.runtime.contracts.research import (
    ResearchRuntimeContract,
)
from app.ai.runtime.generation.validation.service import (
    ValidationService,
)

logger = structlog.get_logger()


def create_validation_registry() -> ValidationRegistry:

    registry = ValidationRegistry()

    #
    # Input
    #

    registry.register_input_validator(
        EmptyPromptValidator(),
    )

    registry.register_input_validator(
        TokenBudgetValidator(),
    )

    registry.register_input_validator(
        ProviderLimitsValidator(),
    )

    registry.register_input_validator(
        ContextValidator(),
    )

    #
    # Output
    #

    registry.register_output_validator(
        JsonValidator(),
    )

    registry.register_output_validator(
        SchemaValidator(),
    )

    registry.register_output_validator(
        CitationValidator(),
    )

    #
    # Hallucination
    #

    registry.register_hallucination_validator(
        HallucinationValidator(),
    )

    #
    # Runtime
    #

    registry.register_runtime_contract(
        ResearchRuntimeContract(),
    )

    return registry


@lru_cache
def get_validation_service() -> ValidationService:

    service = ValidationService(
        registry=create_validation_registry(),
    )

    logger.info(
        "validation.service.initialized",
        validators=service.validator_names,
    )

    return service
