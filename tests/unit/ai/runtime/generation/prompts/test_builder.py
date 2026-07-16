"""
Unit tests for PromptBuilder.

Covers:
- build_from_directory() loads the prompt template text
- build_from_directory() loads and parses prompt metadata
- build_from_directory() loads few-shot examples from examples.json
- Few-shot examples are dropped entirely when few_shot.enabled is False
- Few-shot examples are truncated to few_shot.max_examples when set
- Missing prompt.md raises FileNotFoundError
- Missing metadata.yaml raises FileNotFoundError
- extract_variables() finds every {variable} placeholder, deduplicated
  and sorted
"""

from __future__ import annotations

from pathlib import Path

import pytest
from app.ai.runtime.generation.prompts.builder import PromptBuilder

from tests.unit.ai.runtime.generation.prompts.factories import write_template_dir

# ---------------------------------------------------------------------------
# Prompt loading
# ---------------------------------------------------------------------------


def test_load_prompt(tmp_path: Path) -> None:
    directory = write_template_dir(
        tmp_path / "research" / "v1",
        prompt_text="Context:\n{context}\n\nQuestion:\n{user_input}",
        metadata={"name": "research", "version": "v1"},
    )

    template = PromptBuilder.build_from_directory(directory)

    assert template.template == "Context:\n{context}\n\nQuestion:\n{user_input}"
    assert template.name == "research"
    assert template.version == "v1"


# ---------------------------------------------------------------------------
# Metadata loading
# ---------------------------------------------------------------------------


def test_load_metadata(tmp_path: Path) -> None:
    directory = write_template_dir(
        tmp_path / "research" / "v1",
        metadata={
            "name": "research",
            "version": "v1",
            "title": "Quick Research Response",
            "tags": ["research", "rag"],
            "preferred_providers": ["claude", "openai"],
            "routing": {"quality": "medium", "latency": "low"},
        },
    )

    template = PromptBuilder.build_from_directory(directory)

    assert template.metadata.title == "Quick Research Response"
    assert template.metadata.tags == ["research", "rag"]
    assert template.metadata.preferred_providers == ["claude", "openai"]
    assert template.metadata.routing.quality == "medium"
    assert template.metadata.routing.latency == "low"


# ---------------------------------------------------------------------------
# Examples loading
# ---------------------------------------------------------------------------


def test_load_examples(tmp_path: Path) -> None:
    examples = [
        {"input": "a", "output": "b"},
        {"input": "c", "output": "d"},
    ]
    directory = write_template_dir(
        tmp_path / "research" / "v1",
        metadata={"name": "research", "version": "v1", "few_shot": {"enabled": True}},
        examples=examples,
    )

    template = PromptBuilder.build_from_directory(directory)

    assert template.examples == examples


def test_load_examples_missing_file_defaults_to_empty(tmp_path: Path) -> None:
    directory = write_template_dir(
        tmp_path / "research" / "v1",
        metadata={"name": "research", "version": "v1", "few_shot": {"enabled": True}},
        include_examples_file=False,
    )

    template = PromptBuilder.build_from_directory(directory)

    assert template.examples == []


# ---------------------------------------------------------------------------
# Few shot disabled
# ---------------------------------------------------------------------------


def test_disable_examples(tmp_path: Path) -> None:
    examples = [{"input": "a", "output": "b"}]
    directory = write_template_dir(
        tmp_path / "research" / "v1",
        metadata={"name": "research", "version": "v1", "few_shot": {"enabled": False}},
        examples=examples,
    )

    template = PromptBuilder.build_from_directory(directory)

    assert template.examples == []


# ---------------------------------------------------------------------------
# Max examples
# ---------------------------------------------------------------------------


def test_limit_examples(tmp_path: Path) -> None:
    examples = [
        {"input": "a", "output": "1"},
        {"input": "b", "output": "2"},
        {"input": "c", "output": "3"},
    ]
    directory = write_template_dir(
        tmp_path / "research" / "v1",
        metadata={
            "name": "research",
            "version": "v1",
            "few_shot": {"enabled": True, "max_examples": 2},
        },
        examples=examples,
    )

    template = PromptBuilder.build_from_directory(directory)

    assert template.examples == examples[:2]


def test_limit_examples_zero_means_unlimited(tmp_path: Path) -> None:
    examples = [{"input": "a", "output": "1"}, {"input": "b", "output": "2"}]
    directory = write_template_dir(
        tmp_path / "research" / "v1",
        metadata={
            "name": "research",
            "version": "v1",
            "few_shot": {"enabled": True, "max_examples": 0},
        },
        examples=examples,
    )

    template = PromptBuilder.build_from_directory(directory)

    assert template.examples == examples


# ---------------------------------------------------------------------------
# Missing files
# ---------------------------------------------------------------------------


def test_missing_prompt_file(tmp_path: Path) -> None:
    directory = tmp_path / "research" / "v1"
    directory.mkdir(parents=True)
    (directory / "metadata.yaml").write_text("name: research\nversion: v1\n", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="prompt.md"):
        PromptBuilder.build_from_directory(directory)


def test_missing_metadata_file(tmp_path: Path) -> None:
    directory = tmp_path / "research" / "v1"
    directory.mkdir(parents=True)
    (directory / "prompt.md").write_text("Hello {user_input}", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="metadata.yaml"):
        PromptBuilder.build_from_directory(directory)


# ---------------------------------------------------------------------------
# Variable extraction
# ---------------------------------------------------------------------------


def test_extract_variables() -> None:
    template_text = "Context:\n{context}\n\nQuestion:\n{user_input}\n\nAgain: {context}"

    variables = PromptBuilder.extract_variables(template_text)

    assert variables == ["context", "user_input"]


def test_extract_variables_with_no_placeholders() -> None:
    assert PromptBuilder.extract_variables("no placeholders here") == []
