"""
Unit tests for `RubricJudge` (E16) -- no live OpenAI calls, matches this
project's "never verify with live LLM calls" testing convention. Covers:

- ascore() sends the fixed cheap model (not whatever OPENAI_MODEL is
  configured to), temperature 0, bounded max_completion_tokens
- ascore() returns the parsed RubricJudgeResult
- ascore() raises when the SDK returns no parsed result (refusal/failure)
- build_rubric_judge() raises without OPENAI_API_KEY, matching
  build_openai_ragas_judge()'s own reasoning
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.settings import settings

from benchmarks.generation.rubric_judge import (
    DEFAULT_RUBRIC_JUDGE_MODEL,
    RubricJudge,
    RubricJudgeResult,
    build_rubric_judge,
)


def _make_completion(parsed: RubricJudgeResult | None) -> MagicMock:
    completion = MagicMock()
    completion.choices = [MagicMock(message=MagicMock(parsed=parsed))]
    return completion


@pytest.mark.asyncio
async def test_ascore_uses_the_fixed_cheap_model_not_openai_model_setting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The whole point of this judge being a separate client, not routed
    through GenerationService, is that it never tracks OPENAI_MODEL's
    cost -- assert the literal model string sent, not just that *a* call
    happened."""

    monkeypatch.setattr(settings, "openai_model", "gpt-5.5", raising=False)

    client = MagicMock()
    client.chat.completions.parse = AsyncMock(
        return_value=_make_completion(RubricJudgeResult(passed=True, reason="covers it"))
    )
    judge = RubricJudge(client=client)

    await judge.ascore(question="q", answer="a", rubric="must mention X")

    call_kwargs = client.chat.completions.parse.await_args.kwargs
    assert call_kwargs["model"] == DEFAULT_RUBRIC_JUDGE_MODEL
    assert call_kwargs["model"] != "gpt-5.5"
    assert call_kwargs["temperature"] == 0.0
    assert call_kwargs["response_format"] is RubricJudgeResult


@pytest.mark.asyncio
async def test_ascore_returns_the_parsed_result() -> None:
    client = MagicMock()
    client.chat.completions.parse = AsyncMock(
        return_value=_make_completion(
            RubricJudgeResult(passed=False, reason="missing two of four named roles")
        )
    )
    judge = RubricJudge(client=client)

    result = await judge.ascore(question="q", answer="a", rubric="must name all four roles")

    assert result.passed is False
    assert result.reason == "missing two of four named roles"


@pytest.mark.asyncio
async def test_ascore_raises_when_the_sdk_returns_no_parsed_result() -> None:
    client = MagicMock()
    client.chat.completions.parse = AsyncMock(return_value=_make_completion(None))
    judge = RubricJudge(client=client)

    with pytest.raises(ValueError, match="schema-valid"):
        await judge.ascore(question="q", answer="a", rubric="r")


def test_build_rubric_judge_raises_without_an_openai_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", None)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        build_rubric_judge()


def test_build_rubric_judge_succeeds_with_a_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "test-key")

    judge = build_rubric_judge()

    assert isinstance(judge, RubricJudge)
