from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from app.ai.runtime.generation.enums import (
    GenerationProvider,
)
from pydantic import BaseModel, Field


class FewShotConfig(
    BaseModel,
):
    enabled: bool = False

    selection: str = "static"
    """
    static
    semantic
    dynamic
    """

    max_examples: int = 0


class PromptRoutingConfig(
    BaseModel,
):
    quality: str | None = None
    latency: str | None = None
    cost: str | None = None

    supports_streaming: bool = True

    requires_structured_output: bool = False

    requires_large_context: bool = False


class PromptEvaluationConfig(
    BaseModel,
):
    enable_groundedness: bool = False

    enable_faithfulness: bool = False

    enable_completeness: bool = False

    enable_citation_validation: bool = False

    enable_memory_consistency: bool = False

    enable_plan_quality: bool = False

    enable_contradiction_detection: bool = False


class PromptGenerationConfig(
    BaseModel,
):
    temperature: float | None = None

    max_tokens: int | None = None

    top_p: float | None = None


class PromptContextConfig(
    BaseModel,
):
    max_chunks: int | None = None

    compression_enabled: bool = False

    reranking_required: bool = False

    cross_document_synthesis: bool = False


class PromptMemoryConfig(
    BaseModel,
):
    user_profile_enabled: bool = False

    conversation_summary_enabled: bool = False

    entity_memory_enabled: bool = False

    goal_memory_enabled: bool = False

    task_memory_enabled: bool = False


class PromptArtifactsConfig(
    BaseModel,
):
    persist_prompt: bool = False

    persist_response: bool = True

    persist_evaluation: bool = False

    persist_reasoning: bool = False

    persist_intermediate_reasoning: bool = False


class PromptRuntimeConfig(
    BaseModel,
):
    planner_enabled: bool = False

    reviewer_enabled: bool = False

    query_decomposition_enabled: bool = False

    multi_step_reasoning: bool = False

    tool_selection_enabled: bool = False

    memory_enabled: bool = False


class PromptFutureConfig(
    BaseModel,
):
    supports_agents: bool = False

    supports_memory: bool = False

    supports_mcp: bool = False

    supports_multi_agent_runtime: bool = False

    supports_long_running_tasks: bool = False


class PromptMetadata(
    BaseModel,
):
    #
    # Basic
    #

    title: str | None = None

    description: str | None = None

    tags: list[str] = Field(
        default_factory=list,
    )

    owner: str | None = None

    experimental: bool = False

    recommended_use_cases: list[str] = Field(
        default_factory=list,
    )

    preferred_providers: list[GenerationProvider] = Field(
        default_factory=list,
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            UTC,
        ),
    )

    #
    # Sub-configurations
    #

    few_shot: FewShotConfig = Field(
        default_factory=FewShotConfig,
    )

    routing: PromptRoutingConfig = Field(
        default_factory=PromptRoutingConfig,
    )

    evaluation: PromptEvaluationConfig = Field(
        default_factory=PromptEvaluationConfig,
    )

    generation: PromptGenerationConfig = Field(
        default_factory=PromptGenerationConfig,
    )

    context: PromptContextConfig = Field(
        default_factory=PromptContextConfig,
    )

    memory: PromptMemoryConfig = Field(
        default_factory=PromptMemoryConfig,
    )

    artifacts: PromptArtifactsConfig = Field(
        default_factory=PromptArtifactsConfig,
    )

    runtime: PromptRuntimeConfig = Field(
        default_factory=PromptRuntimeConfig,
    )

    future: PromptFutureConfig = Field(
        default_factory=PromptFutureConfig,
    )


class PromptTemplate(
    BaseModel,
):
    id: UUID = Field(
        default_factory=uuid4,
    )

    name: str

    version: str

    template: str

    variables: list[str]

    examples: list[dict[str, Any]] = Field(
        default_factory=list,
    )

    metadata: PromptMetadata


class PromptRenderRequest(
    BaseModel,
):
    template_name: str

    version: str | None = None

    variables: dict[
        str,
        Any,
    ]

    examples: list[dict[str, Any]] = Field(
        default_factory=list,
    )

    override_provider: GenerationProvider | None = None

    session_id: UUID | None = None

    user_id: UUID | None = None


class PromptRenderResult(
    BaseModel,
):
    template_name: str

    version: str

    rendered_prompt: str

    estimated_tokens: int | None = None

    metadata: PromptMetadata
