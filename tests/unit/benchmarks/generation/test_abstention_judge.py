"""
Unit tests for `AbstentionJudge` -- no live OpenAI calls, matches this
project's "never verify with live LLM calls" testing convention. Mirrors
`test_rubric_judge.py`'s established pattern; covers what's genuinely
different here: the optional `rubric` (falls back to a generic
insufficient-evidence criterion when the example has none, unlike E16's
rubric judge, which requires one).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.settings import settings

from benchmarks.generation.abstention_judge import (
    DEFAULT_ABSTENTION_JUDGE_MODEL,
    AbstentionJudge,
    AbstentionJudgeResult,
    build_abstention_judge,
)


def _make_completion(parsed: AbstentionJudgeResult | None) -> MagicMock:
    completion = MagicMock()
    completion.choices = [MagicMock(message=MagicMock(parsed=parsed))]
    return completion


@pytest.mark.asyncio
async def test_ascore_uses_the_fixed_cheap_model_not_openai_model_setting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "openai_model", "gpt-5.5", raising=False)

    client = MagicMock()
    client.chat.completions.parse = AsyncMock(
        return_value=_make_completion(AbstentionJudgeResult(passed=True, reason="declined"))
    )
    judge = AbstentionJudge(client=client)

    await judge.ascore(question="q", answer="a", rubric="should have abstained")

    call_kwargs = client.chat.completions.parse.await_args.kwargs
    assert call_kwargs["model"] == DEFAULT_ABSTENTION_JUDGE_MODEL
    assert call_kwargs["model"] != "gpt-5.5"
    assert call_kwargs["temperature"] == 0.0
    assert call_kwargs["response_format"] is AbstentionJudgeResult


@pytest.mark.asyncio
async def test_ascore_falls_back_to_a_generic_criterion_when_no_rubric_is_set() -> None:
    """Most unanswerable golden examples have no per-example rubric --
    the judge must still work for them, not just the ~12% with one."""

    client = MagicMock()
    client.chat.completions.parse = AsyncMock(
        return_value=_make_completion(AbstentionJudgeResult(passed=True, reason="declined"))
    )
    judge = AbstentionJudge(client=client)

    await judge.ascore(question="q", answer="a", rubric=None)

    sent_content = client.chat.completions.parse.await_args.kwargs["messages"][1]["content"]
    assert "does not support a confident answer" in sent_content


@pytest.mark.asyncio
async def test_ascore_uses_the_given_rubric_when_present() -> None:
    client = MagicMock()
    client.chat.completions.parse = AsyncMock(
        return_value=_make_completion(AbstentionJudgeResult(passed=False, reason="answered anyway"))
    )
    judge = AbstentionJudge(client=client)

    await judge.ascore(question="q", answer="a", rubric="corpus has no relevant coverage")

    sent_content = client.chat.completions.parse.await_args.kwargs["messages"][1]["content"]
    assert "corpus has no relevant coverage" in sent_content


@pytest.mark.asyncio
async def test_ascore_returns_the_parsed_result() -> None:
    client = MagicMock()
    client.chat.completions.parse = AsyncMock(
        return_value=_make_completion(
            AbstentionJudgeResult(passed=False, reason="confidently fabricated an answer")
        )
    )
    judge = AbstentionJudge(client=client)

    result = await judge.ascore(question="q", answer="a")

    assert result.passed is False
    assert result.reason == "confidently fabricated an answer"


@pytest.mark.asyncio
async def test_ascore_raises_when_the_sdk_returns_no_parsed_result() -> None:
    client = MagicMock()
    client.chat.completions.parse = AsyncMock(return_value=_make_completion(None))
    judge = AbstentionJudge(client=client)

    with pytest.raises(ValueError, match="schema-valid"):
        await judge.ascore(question="q", answer="a")


def test_build_abstention_judge_raises_without_an_openai_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "openai_api_key", None)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        build_abstention_judge()


def test_build_abstention_judge_succeeds_with_a_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "test-key")

    judge = build_abstention_judge()

    assert isinstance(judge, AbstentionJudge)
