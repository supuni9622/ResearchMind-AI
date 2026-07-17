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
from app.ai.runtime.generation.validation.output.completeness_validator import (
    CompletenessValidator,
)
from app.ai.runtime.generation.validation.output.consistency_validator import (
    ConsistencyValidator,
)
from app.ai.runtime.generation.validation.output.formatting_validator import (
    FormattingValidator,
)
from app.ai.runtime.generation.validation.output.hallucination_validator import (
    HallucinationValidator,
)
from app.ai.runtime.generation.validation.output.json_validator import (
    JsonValidator,
)
from app.ai.runtime.generation.validation.output.response_size_validator import (
    ResponseSizeValidator,
)
from app.ai.runtime.generation.validation.output.schema_validator import (
    SchemaValidator,
)
from app.ai.runtime.generation.validation.registry import (
    ValidationRegistry,
)
from app.ai.runtime.generation.validation.runtime.contracts.agent import (
    AgentRuntimeContract,
)
from app.ai.runtime.generation.validation.runtime.contracts.mcp import (
    MCPRuntimeContract,
)
from app.ai.runtime.generation.validation.runtime.contracts.planner import (
    PlannerRuntimeContract,
)
from app.ai.runtime.generation.validation.runtime.contracts.research import (
    ResearchRuntimeContract,
)
from app.ai.runtime.generation.validation.runtime.contracts.reviewer import (
    ReviewerRuntimeContract,
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
    # Pipeline order: JSON -> Schema -> Formatting -> Completeness ->
    # Consistency -> Response Size -> Citation. Registration order is
    # execution order (see ValidationRegistry) -- this only affects the
    # order issues appear in, since every validator here always runs
    # regardless of what an earlier one found.
    #

    registry.register_output_validator(
        JsonValidator(),
    )

    registry.register_output_validator(
        SchemaValidator(),
    )

    registry.register_output_validator(
        FormattingValidator(),
    )

    registry.register_output_validator(
        CompletenessValidator(),
    )

    registry.register_output_validator(
        ConsistencyValidator(),
    )

    registry.register_output_validator(
        ResponseSizeValidator(),
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
    # Planner/Reviewer/Agent/MCP are registered but dormant in
    # production today: `RuntimeValidationService` only runs a
    # contract when `GenerationRequest.runtime` matches it, and
    # nothing sets `runtime` to those values yet (no Planner/Reviewer/
    # Agent/MCP runtime exists in this codebase). Registering them now
    # means the day one of those runtimes starts issuing requests with
    # `runtime` set, its contract is already active with no further
    # wiring here.
    #

    registry.register_runtime_contract(
        ResearchRuntimeContract(),
    )

    registry.register_runtime_contract(
        PlannerRuntimeContract(),
    )

    registry.register_runtime_contract(
        ReviewerRuntimeContract(),
    )

    registry.register_runtime_contract(
        AgentRuntimeContract(),
    )

    registry.register_runtime_contract(
        MCPRuntimeContract(),
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
