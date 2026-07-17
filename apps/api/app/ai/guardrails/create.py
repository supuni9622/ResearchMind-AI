from __future__ import annotations

from functools import lru_cache

import structlog

from app.ai.guardrails.artifacts.writers import GuardrailArtifactWriter
from app.ai.guardrails.generation.faithfulness import FaithfulnessGuardrail
from app.ai.guardrails.generation.moderation import (
    AlwaysAllowModerationProvider,
    ModerationGuardrail,
)
from app.ai.guardrails.generation.pii_leakage import PiiLeakageGuardrail
from app.ai.guardrails.generation.schema_enforcement import SchemaEnforcementGuardrail
from app.ai.guardrails.input.pii_detection import PiiDetectionGuardrail
from app.ai.guardrails.input.prompt_injection import PromptInjectionGuardrail
from app.ai.guardrails.input.rate_limit import RateLimitGuardrail
from app.ai.guardrails.input.scope_validation import ScopeValidationGuardrail
from app.ai.guardrails.input.toxicity import ToxicityGuardrail
from app.ai.guardrails.registry import GuardrailRegistry
from app.ai.guardrails.retrieval.access_control import (
    AccessControlGuardrail,
    PermissiveAccessControlProvider,
)
from app.ai.guardrails.retrieval.citation_integrity import CitationIntegrityGuardrail
from app.ai.guardrails.retrieval.context_sanitization import ContextSanitizationGuardrail
from app.ai.guardrails.retrieval.source_trust import SourceTrustGuardrail
from app.ai.guardrails.runtime.budget_guardrail import BudgetGuardrail
from app.ai.guardrails.runtime.loop_detection import LoopDetectionGuardrail
from app.ai.guardrails.runtime.tool_policy import AllowAllToolPolicyProvider, ToolPolicyGuardrail
from app.ai.guardrails.service import GuardrailService
from app.ai.guardrails.trust.trust_registry import TrustRegistry
from app.ai.knowledge.context.guardrails.create import create_context_guardrail_service
from app.ai.runtime.generation.validation.output.hallucination_validator import (
    HallucinationValidator,
)
from app.ai.runtime.generation.validation.output.json_validator import JsonValidator
from app.ai.runtime.generation.validation.output.schema_validator import SchemaValidator
from app.core.settings import settings
from app.infrastructure.metrics.noop import NoOpMetricsRecorder
from app.infrastructure.storage import create_storage

logger = structlog.get_logger()


def create_guardrail_registry() -> GuardrailRegistry:

    registry = GuardrailRegistry()

    #
    # Input (PRD §8)
    #

    registry.register_input_guardrail(
        PromptInjectionGuardrail(),
    )

    registry.register_input_guardrail(
        ScopeValidationGuardrail(),
    )

    registry.register_input_guardrail(
        PiiDetectionGuardrail(),
    )

    registry.register_input_guardrail(
        RateLimitGuardrail(),
    )

    registry.register_input_guardrail(
        ToxicityGuardrail(),
    )

    #
    # Retrieval (PRD §9)
    #

    registry.register_retrieval_guardrail(
        ContextSanitizationGuardrail(
            create_context_guardrail_service(),
        ),
    )

    registry.register_retrieval_guardrail(
        SourceTrustGuardrail(
            TrustRegistry(),
        ),
    )

    registry.register_retrieval_guardrail(
        CitationIntegrityGuardrail(),
    )

    registry.register_retrieval_guardrail(
        AccessControlGuardrail(
            PermissiveAccessControlProvider(),
        ),
    )

    #
    # Generation (PRD §10)
    #

    registry.register_generation_guardrail(
        FaithfulnessGuardrail(
            HallucinationValidator(),
        ),
    )

    registry.register_generation_guardrail(
        SchemaEnforcementGuardrail(
            SchemaValidator(),
            JsonValidator(),
        ),
    )

    registry.register_generation_guardrail(
        PiiLeakageGuardrail(),
    )

    registry.register_generation_guardrail(
        ModerationGuardrail(
            AlwaysAllowModerationProvider(),
        ),
    )

    #
    # Runtime (PRD §11)
    #
    # `approval_gate.py`'s `ApprovalGateInterface` is deliberately not
    # registered here -- it isn't a `RuntimeGuardrailInterface` at all,
    # see its module docstring.
    #

    registry.register_runtime_guardrail(
        BudgetGuardrail(),
    )

    registry.register_runtime_guardrail(
        LoopDetectionGuardrail(),
    )

    registry.register_runtime_guardrail(
        ToolPolicyGuardrail(
            AllowAllToolPolicyProvider(),
        ),
    )

    return registry


def create_guardrail_artifact_writer() -> GuardrailArtifactWriter:

    return GuardrailArtifactWriter(
        storage_provider=create_storage(settings),
    )


@lru_cache
def get_guardrail_service() -> GuardrailService:

    service = GuardrailService(
        registry=create_guardrail_registry(),
        artifact_writer=create_guardrail_artifact_writer(),
        metrics=NoOpMetricsRecorder(),
    )

    logger.info(
        "guardrails.service.initialized",
        guardrails=service.guardrail_names,
    )

    return service
