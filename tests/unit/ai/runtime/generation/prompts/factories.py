"""
Shared test factories for Prompts Platform unit tests.

Not a test module itself (no test_ prefix) -- imported by the actual
test files under tests/unit/ai/runtime/generation/prompts/.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import yaml
from app.ai.runtime.generation.prompts import registry as registry_module
from app.ai.runtime.generation.prompts.models import PromptMetadata, PromptTemplate

# The on-disk template tree shipped with the app, resolved via the
# registry module's own location so these tests work regardless of the
# process cwd.
TEMPLATES_ROOT: Path = Path(registry_module.__file__).resolve().parent / "templates"


def make_metadata(**overrides: Any) -> PromptMetadata:
    return PromptMetadata(**overrides)


def make_template(
    *,
    name: str = "research",
    version: str = "v1",
    template: str = "Context:\n{context}\n\nQuestion:\n{user_input}",
    variables: list[str] | None = None,
    examples: list[dict[str, Any]] | None = None,
    metadata: PromptMetadata | None = None,
) -> PromptTemplate:
    return PromptTemplate(
        name=name,
        version=version,
        template=template,
        variables=variables if variables is not None else ["context", "user_input"],
        examples=examples or [],
        metadata=metadata or make_metadata(),
    )


def write_template_dir(
    directory: Path,
    *,
    prompt_text: str = "Context:\n{context}\n\nQuestion:\n{user_input}",
    metadata: dict[str, Any] | None = None,
    examples: list[dict[str, Any]] | None = None,
    include_examples_file: bool = True,
) -> Path:
    """
    Writes a prompt.md / metadata.yaml / examples.json triple to `directory`,
    mirroring the on-disk shape PromptBuilder.build_from_directory() expects.
    """

    directory.mkdir(parents=True, exist_ok=True)

    (directory / "prompt.md").write_text(prompt_text, encoding="utf-8")

    metadata_data: dict[str, Any] = {"name": "test_prompt", "version": "v1"}

    if metadata:
        metadata_data.update(metadata)

    (directory / "metadata.yaml").write_text(
        yaml.safe_dump(metadata_data),
        encoding="utf-8",
    )

    if include_examples_file:
        (directory / "examples.json").write_text(
            json.dumps(examples if examples is not None else []),
            encoding="utf-8",
        )

    return directory


def make_token_counter(*, return_value: int = 100) -> AsyncMock:
    """
    A fake TokenCounter for unit tests.

    The real TokenCounter dials out to Anthropic/Gemini for some
    providers and can't even be constructed without API keys, so
    PromptService unit tests inject this instead.
    """

    counter = AsyncMock()
    counter.count = AsyncMock(return_value=return_value)
    return counter
