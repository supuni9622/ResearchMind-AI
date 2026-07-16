"""
Unit tests covering few-shot example selection at build time.

Only "static" passthrough selection exists today -- "semantic" and
"dynamic" selection strategies are recorded in FewShotConfig.selection
but PromptBuilder does not yet branch on the value. These tests pin the
current contract so a future selection engine lands as a deliberate
change rather than a silent behavior shift:

Covers:
- few_shot.enabled=False drops examples regardless of the configured
  selection strategy
- few_shot.enabled=True with selection="static" passes examples through
  unfiltered
"""

from __future__ import annotations

from pathlib import Path

from app.ai.runtime.generation.prompts.builder import PromptBuilder

from tests.unit.ai.runtime.generation.prompts.factories import write_template_dir

# ---------------------------------------------------------------------------
# Semantic examples disabled
# ---------------------------------------------------------------------------


def test_semantic_examples_disabled(tmp_path: Path) -> None:
    examples = [{"input": "a", "output": "b"}]
    directory = write_template_dir(
        tmp_path / "research" / "v1",
        metadata={
            "name": "research",
            "version": "v1",
            "few_shot": {"enabled": False, "selection": "semantic"},
        },
        examples=examples,
    )

    template = PromptBuilder.build_from_directory(directory)

    assert template.examples == []
    assert template.metadata.few_shot.enabled is False
    assert template.metadata.few_shot.selection == "semantic"


# ---------------------------------------------------------------------------
# Static examples
# ---------------------------------------------------------------------------


def test_static_examples(tmp_path: Path) -> None:
    examples = [
        {"input": "a", "output": "1"},
        {"input": "b", "output": "2"},
    ]
    directory = write_template_dir(
        tmp_path / "research" / "v1",
        metadata={
            "name": "research",
            "version": "v1",
            "few_shot": {"enabled": True, "selection": "static"},
        },
        examples=examples,
    )

    template = PromptBuilder.build_from_directory(directory)

    assert template.examples == examples
    assert template.metadata.few_shot.selection == "static"
