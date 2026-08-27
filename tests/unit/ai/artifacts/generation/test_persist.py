"""
Unit tests for `persist_generation_artifact()` (Evaluation Platform Gap
1, streaming follow-up, 2026-08-12) -- shared between `GenerationService.
generate()` and `StreamingService._stream_live()` so both a non-streamed
and a streamed answer-producing call persist the exact same
`GenerationArtifact` shape, gated by the same `(runtime, GENERATION)`
policy check.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from app.ai.artifacts.enums import ArtifactCategory, ArtifactPolicy, ArtifactRuntime
from app.ai.artifacts.generation.persist import persist_generation_artifact
from app.ai.artifacts.policies.models import ArtifactPolicyRule
from app.ai.artifacts.policies.service import ArtifactPolicyService
from app.ai.knowledge.context.models import PromptContext
from app.ai.runtime.generation.models import GenerationRequest


@pytest.mark.asyncio
async def test_writes_the_artifact_when_policy_allows(generation_result) -> None:
    request = GenerationRequest(
        prompt_context=PromptContext(context="", chunks=[]),
        user_prompt="hello",
        artifact_runtime=ArtifactRuntime.RESEARCH,
    )
    artifact_writer = AsyncMock()

    await persist_generation_artifact(
        request=request,
        result=generation_result,
        artifact_writer=artifact_writer,
        artifact_policy_service=ArtifactPolicyService(
            rules=[
                ArtifactPolicyRule(
                    runtime=ArtifactRuntime.RESEARCH,
                    category=ArtifactCategory.GENERATION,
                    policy=ArtifactPolicy.PERMANENT,
                ),
            ]
        ),
    )

    artifact_writer.write.assert_awaited_once()
    written = artifact_writer.write.await_args.args[0]
    assert written.response.content == generation_result.content


@pytest.mark.asyncio
async def test_skips_the_write_when_policy_denies(generation_result) -> None:
    request = GenerationRequest(
        prompt_context=PromptContext(context="", chunks=[]),
        user_prompt="hello",
        artifact_runtime=ArtifactRuntime.RESEARCH,
    )
    artifact_writer = AsyncMock()

    await persist_generation_artifact(
        request=request,
        result=generation_result,
        artifact_writer=artifact_writer,
        artifact_policy_service=ArtifactPolicyService(rules=[]),
    )

    artifact_writer.write.assert_not_awaited()


@pytest.mark.asyncio
async def test_defaults_to_chat_runtime_when_unset(generation_result) -> None:
    """No artifact_runtime set on the request -> falls back to CHAT,
    matching GenerationService.generate()'s own default."""

    request = GenerationRequest(
        prompt_context=PromptContext(context="", chunks=[]),
        user_prompt="hello",
    )
    artifact_writer = AsyncMock()

    await persist_generation_artifact(
        request=request,
        result=generation_result,
        artifact_writer=artifact_writer,
        artifact_policy_service=ArtifactPolicyService(),
    )

    artifact_writer.write.assert_awaited_once()


@pytest.mark.asyncio
async def test_no_policy_service_persists_unconditionally(generation_result) -> None:
    """`artifact_policy_service=None` skips the policy check entirely --
    matches GenerationService.generate()'s existing behavior when no
    policy service is wired at all."""

    request = GenerationRequest(
        prompt_context=PromptContext(context="", chunks=[]),
        user_prompt="hello",
        artifact_runtime=ArtifactRuntime.RESEARCH,
    )
    artifact_writer = AsyncMock()

    await persist_generation_artifact(
        request=request,
        result=generation_result,
        artifact_writer=artifact_writer,
        artifact_policy_service=None,
    )

    artifact_writer.write.assert_awaited_once()


@pytest.mark.asyncio
async def test_write_failure_is_caught_not_raised(generation_result) -> None:
    request = GenerationRequest(
        prompt_context=PromptContext(context="", chunks=[]),
        user_prompt="hello",
    )
    artifact_writer = AsyncMock()
    artifact_writer.write = AsyncMock(side_effect=RuntimeError("storage unavailable"))

    await persist_generation_artifact(
        request=request,
        result=generation_result,
        artifact_writer=artifact_writer,
        artifact_policy_service=ArtifactPolicyService(),
    )
