"""
Unit tests for PromptFactory.

Covers:
- build() with no examples produces a system + human message pair
- build() with examples inserts a few-shot block between system and human
- build() treats an empty/omitted examples list the same as no examples
"""

from __future__ import annotations

from app.ai.runtime.generation.prompts.langchain.prompt_factory import PromptFactory
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from tests.unit.ai.runtime.generation.prompts.factories import make_template

# ---------------------------------------------------------------------------
# ChatPromptTemplate build
# ---------------------------------------------------------------------------


def test_build_prompt() -> None:
    template = make_template()

    prompt = PromptFactory.build(template)
    messages = prompt.invoke({"context": "ctx", "user_input": "question"}).to_messages()

    assert len(messages) == 2
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], HumanMessage)
    assert messages[1].content == "question"
    assert "ctx" in messages[0].content


# ---------------------------------------------------------------------------
# Few shot support
# ---------------------------------------------------------------------------


def test_build_with_examples() -> None:
    template = make_template()
    examples = [
        {"input": "example question 1", "output": "example answer 1"},
        {"input": "example question 2", "output": "example answer 2"},
    ]

    prompt = PromptFactory.build(template, examples)
    messages = prompt.invoke({"context": "ctx", "user_input": "question"}).to_messages()

    # system + 2*(human/ai example pair) + final human
    assert len(messages) == 6

    assert isinstance(messages[0], SystemMessage)

    assert isinstance(messages[1], HumanMessage)
    assert messages[1].content == "example question 1"

    assert isinstance(messages[2], AIMessage)
    assert messages[2].content == "example answer 1"

    assert isinstance(messages[3], HumanMessage)
    assert messages[3].content == "example question 2"

    assert isinstance(messages[4], AIMessage)
    assert messages[4].content == "example answer 2"

    assert isinstance(messages[5], HumanMessage)
    assert messages[5].content == "question"


# ---------------------------------------------------------------------------
# No examples
# ---------------------------------------------------------------------------


def test_build_without_examples() -> None:
    template = make_template()

    prompt_none = PromptFactory.build(template, None)
    prompt_empty = PromptFactory.build(template, [])

    for prompt in (prompt_none, prompt_empty):
        messages = prompt.invoke({"context": "ctx", "user_input": "question"}).to_messages()

        assert len(messages) == 2
        assert isinstance(messages[0], SystemMessage)
        assert isinstance(messages[1], HumanMessage)
