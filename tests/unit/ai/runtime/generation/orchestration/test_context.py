"""
Unit tests for GenerationExecutionContext.

Covers:
- for_request() derives request_id/runtime/session_id from the request
- for_request() only sets artifact_metadata when artifact_runtime is set
- finalize() copies provider/routing/cache/validation/guardrails off a result
- finalize() sets completed_at
"""

from __future__ import annotations

from uuid import uuid4

from app.ai.artifacts.enums import ArtifactRuntime
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.orchestration.context import (
    GenerationExecutionContext,
)
from app.ai.runtime.generation.validation.runtime.enums import RuntimeType

from tests.unit.ai.runtime.generation.orchestration.factories import (
    make_request,
    make_result,
)


def test_for_request_derives_identity_fields() -> None:
    request_id = uuid4()

    session_id = uuid4()

    request = make_request(
        runtime=RuntimeType.RESEARCH,
        session_id=session_id,
        request_id=request_id,
    )

    context = GenerationExecutionContext.for_request(request)

    assert context.request_id == request_id
    assert context.runtime == RuntimeType.RESEARCH
    assert context.session_id == session_id
    assert context.trace_id is not None
    assert context.completed_at is None


def test_for_request_without_artifact_runtime_leaves_artifact_metadata_none() -> None:
    context = GenerationExecutionContext.for_request(make_request())

    assert context.artifact_metadata is None


def test_for_request_with_artifact_runtime_populates_artifact_metadata() -> None:
    request = make_request().model_copy(
        update={"artifact_runtime": ArtifactRuntime.CHAT},
    )

    context = GenerationExecutionContext.for_request(request)

    assert context.artifact_metadata == {"runtime": ArtifactRuntime.CHAT.value}


def test_finalize_copies_result_fields_and_sets_completed_at() -> None:
    request = make_request()

    context = GenerationExecutionContext.for_request(request)

    result = make_result(
        request=request,
        metadata={
            "routing": {"strategy": "auto", "selected_provider": "groq"},
            "cache": {"hit": True, "level": "l1"},
        },
    )

    context.finalize(result)

    assert context.provider == GenerationProvider.GROQ
    assert context.routing_decision == {"strategy": "auto", "selected_provider": "groq"}
    assert context.cache_decision == {"hit": True, "level": "l1"}
    assert context.validation_report is result.validation
    assert context.guardrail_report is result.guardrails
    assert context.completed_at is not None
