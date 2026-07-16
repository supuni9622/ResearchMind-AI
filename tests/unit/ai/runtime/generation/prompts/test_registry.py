"""
Unit tests for PromptRegistry.

Covers:
- register() stores a template, retrievable via get()
- get() with no version returns the latest version
- get() with an explicit version returns that exact version
- get() raises ValueError for an unknown name/version
- exists() reflects registration state for name and name+version
- list_names() returns all registered prompt names, sorted
- versions() returns all registered versions for a name, sorted
- preferred_providers() / metadata() surface template metadata
- register_all() walks the on-disk template tree and registers every
  prompt/version directory, skipping directories that fail to build
"""

from __future__ import annotations

from pathlib import Path

import pytest
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.prompts.registry import PromptRegistry

from tests.unit.ai.runtime.generation.prompts.factories import (
    TEMPLATES_ROOT,
    make_metadata,
    make_template,
    write_template_dir,
)

# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def test_register_prompt() -> None:
    registry = PromptRegistry()
    template = make_template(name="research", version="v1")

    registry.register(template)

    assert registry.get("research", "v1") is template
    assert registry.total_prompts() == 1


# ---------------------------------------------------------------------------
# Get latest version
# ---------------------------------------------------------------------------


def test_get_latest_version() -> None:
    registry = PromptRegistry()
    v1 = make_template(name="research", version="v1")
    v2 = make_template(name="research", version="v2")

    registry.register(v1)
    registry.register(v2)

    latest = registry.get("research")

    assert latest is v2
    assert latest.version == "v2"


# ---------------------------------------------------------------------------
# Get specific version
# ---------------------------------------------------------------------------


def test_get_specific_version() -> None:
    registry = PromptRegistry()
    v1 = make_template(name="research", version="v1")
    v2 = make_template(name="research", version="v2")

    registry.register(v1)
    registry.register(v2)

    assert registry.get("research", "v1") is v1


def test_get_unknown_name_raises() -> None:
    registry = PromptRegistry()

    with pytest.raises(ValueError, match="research"):
        registry.get("research")


def test_get_unknown_version_raises() -> None:
    registry = PromptRegistry()
    registry.register(make_template(name="research", version="v1"))

    with pytest.raises(ValueError, match="v9"):
        registry.get("research", "v9")


# ---------------------------------------------------------------------------
# Exists
# ---------------------------------------------------------------------------


def test_exists() -> None:
    registry = PromptRegistry()
    registry.register(make_template(name="research", version="v1"))

    assert registry.exists("research") is True
    assert registry.exists("research", "v1") is True
    assert registry.exists("research", "v2") is False
    assert registry.exists("chat") is False


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


def test_list_prompts() -> None:
    registry = PromptRegistry()
    registry.register(make_template(name="research", version="v1"))
    registry.register(make_template(name="chat", version="v1"))
    registry.register(make_template(name="summary", version="v1"))

    assert registry.list_names() == ["chat", "research", "summary"]


def test_list_prompts_empty_registry() -> None:
    assert PromptRegistry().list_names() == []


# ---------------------------------------------------------------------------
# Versions
# ---------------------------------------------------------------------------


def test_versions() -> None:
    registry = PromptRegistry()
    registry.register(make_template(name="research", version="v2"))
    registry.register(make_template(name="research", version="v1"))

    assert registry.versions("research") == ["v1", "v2"]


def test_versions_for_unknown_name_is_empty() -> None:
    registry = PromptRegistry()

    assert registry.versions("research") == []


# ---------------------------------------------------------------------------
# Metadata helpers
# ---------------------------------------------------------------------------


def test_preferred_providers() -> None:
    registry = PromptRegistry()
    metadata = make_metadata(
        preferred_providers=[GenerationProvider.CLAUDE, GenerationProvider.OPENAI],
    )
    registry.register(make_template(name="research", version="v1", metadata=metadata))

    assert registry.preferred_providers("research", "v1") == [
        GenerationProvider.CLAUDE,
        GenerationProvider.OPENAI,
    ]


def test_metadata_helper_returns_template_metadata() -> None:
    registry = PromptRegistry()
    metadata = make_metadata(title="Research Prompt")
    registry.register(make_template(name="research", version="v1", metadata=metadata))

    assert registry.metadata("research", "v1").title == "Research Prompt"


# ---------------------------------------------------------------------------
# Startup registration
# ---------------------------------------------------------------------------


def test_register_all() -> None:
    registry = PromptRegistry()

    registry.register_all(TEMPLATES_ROOT)

    assert registry.total_prompts() == 7
    assert registry.dump() == {
        "research": ["v1", "v2"],
        "chat": ["v1", "v2", "v3"],
        "summary": ["v1", "v2"],
    }

    latest_research = registry.get("research")
    assert latest_research.version == "v2"


def test_register_all_skips_broken_directories(tmp_path: Path) -> None:
    root = tmp_path / "templates"

    write_template_dir(
        root / "research" / "v1",
        metadata={"name": "research", "version": "v1"},
    )

    broken = root / "research" / "v2"
    broken.mkdir(parents=True)
    (broken / "prompt.md").write_text("Missing metadata file", encoding="utf-8")

    registry = PromptRegistry()
    registry.register_all(root)

    assert registry.total_prompts() == 1
    assert registry.exists("research", "v1")
    assert not registry.exists("research", "v2")


def test_register_all_missing_root_directory_is_noop(tmp_path: Path) -> None:
    registry = PromptRegistry()

    registry.register_all(tmp_path / "does_not_exist")

    assert registry.total_prompts() == 0
