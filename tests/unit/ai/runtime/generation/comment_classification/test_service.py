from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.ai.runtime.generation.comment_classification.models import (
    CommentClassificationDecision,
)
from app.ai.runtime.generation.comment_classification.service import (
    CommentClassificationService,
)
from app.ai.runtime.generation.enums import GenerationProvider
from app.models.enums import CommentClassification


@pytest.mark.asyncio
async def test_uses_the_cheap_provider_when_configured() -> None:
    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(
        parsed_output=CommentClassificationDecision(
            classification=CommentClassification.OBJECTIVE,
            reason="cites the wrong paper",
        ),
    )
    service = CommentClassificationService(
        cheap_generation_runtime=runtime, cheap_provider=GenerationProvider.OPENAI
    )

    decision = await service.classify(
        comment="this cited the wrong paper", owner_id=uuid4(), generation_id=uuid4()
    )

    assert decision.classification is CommentClassification.OBJECTIVE
    runtime.execute.assert_awaited_once()
    assert runtime.execute.await_args.kwargs["provider"] == GenerationProvider.OPENAI


@pytest.mark.asyncio
async def test_falls_back_to_the_shared_runtime_when_no_cheap_provider_configured() -> None:
    cheap_runtime = AsyncMock()
    fallback_runtime = AsyncMock()
    fallback_runtime.execute.return_value = SimpleNamespace(
        parsed_output=CommentClassificationDecision(
            classification=CommentClassification.PREFERENCE,
            reason="too formal",
        ),
    )
    service = CommentClassificationService(
        cheap_generation_runtime=cheap_runtime,
        cheap_provider=None,
        fallback_generation_runtime=fallback_runtime,
    )

    decision = await service.classify(
        comment="this answer was too formal", owner_id=uuid4(), generation_id=uuid4()
    )

    assert decision.classification is CommentClassification.PREFERENCE
    cheap_runtime.execute.assert_not_awaited()
    fallback_runtime.execute.assert_awaited_once()
    assert fallback_runtime.execute.await_args.kwargs["provider"] is None


@pytest.mark.asyncio
async def test_model_failure_fails_closed_to_preference() -> None:
    """The conservative default: an unclassifiable comment must never be
    treated as objective, since that's the direction that can contaminate
    the shared golden set."""

    runtime = AsyncMock()
    runtime.execute.side_effect = RuntimeError("provider unavailable")
    service = CommentClassificationService(
        cheap_generation_runtime=runtime, cheap_provider=GenerationProvider.OPENAI
    )

    decision = await service.classify(
        comment="some comment", owner_id=uuid4(), generation_id=uuid4()
    )

    assert decision.classification is CommentClassification.PREFERENCE


@pytest.mark.asyncio
async def test_schema_invalid_response_fails_closed_to_preference() -> None:
    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(parsed_output={"not": "the right shape"})
    service = CommentClassificationService(
        cheap_generation_runtime=runtime, cheap_provider=GenerationProvider.OPENAI
    )

    decision = await service.classify(
        comment="some comment", owner_id=uuid4(), generation_id=uuid4()
    )

    assert decision.classification is CommentClassification.PREFERENCE


@pytest.mark.asyncio
async def test_dict_parsed_output_is_coerced_into_the_model() -> None:
    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(
        parsed_output={"classification": "objective", "reason": "wrong citation"}
    )
    service = CommentClassificationService(
        cheap_generation_runtime=runtime, cheap_provider=GenerationProvider.OPENAI
    )

    decision = await service.classify(
        comment="wrong citation", owner_id=uuid4(), generation_id=uuid4()
    )

    assert decision.classification is CommentClassification.OBJECTIVE
    assert decision.reason == "wrong citation"


@pytest.mark.asyncio
async def test_long_comment_is_bounded_before_being_sent_to_the_model() -> None:
    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(
        parsed_output=CommentClassificationDecision(
            classification=CommentClassification.PREFERENCE, reason="r"
        ),
    )
    service = CommentClassificationService(
        cheap_generation_runtime=runtime, cheap_provider=GenerationProvider.OPENAI
    )

    await service.classify(comment="x" * 5000, owner_id=uuid4(), generation_id=uuid4())

    request = runtime.execute.await_args.args[0]
    assert len(request.user_prompt) < 2100
