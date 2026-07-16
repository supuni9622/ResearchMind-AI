from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml
from app.ai.runtime.generation.prompts.models import (
    PromptMetadata,
    PromptTemplate,
)


class PromptBuilder:
    @staticmethod
    def build_from_directory(
        directory: Path,
    ) -> PromptTemplate:

        prompt_file = directory / "prompt.md"

        metadata_file = directory / "metadata.yaml"

        examples_file = directory / "examples.json"

        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

        if not metadata_file.exists():
            raise FileNotFoundError(f"Metadata file not found: {metadata_file}")

        #
        # Load prompt
        #

        template_text = prompt_file.read_text(
            encoding="utf-8",
        )

        #
        # Load metadata
        #

        metadata_data: dict[
            str,
            Any,
        ] = yaml.safe_load(
            metadata_file.read_text(
                encoding="utf-8",
            )
        )

        name = metadata_data.pop("name")

        version = metadata_data.pop("version")

        metadata = PromptMetadata(
            **metadata_data,
        )

        #
        # Load examples
        #

        examples: list[dict[str, Any]] = []

        if examples_file.exists():
            examples = json.loads(
                examples_file.read_text(
                    encoding="utf-8",
                )
            )

        #
        # Few shot optimization
        #

        few_shot_config = metadata_data.get(
            "few_shot",
            {},
        )

        enabled = few_shot_config.get(
            "enabled",
            False,
        )

        max_examples = few_shot_config.get(
            "max_examples",
            0,
        )

        if not enabled:
            examples = []

        elif max_examples > 0:
            examples = examples[:max_examples]

        #
        # Extract variables
        #

        variables = PromptBuilder.extract_variables(
            template_text,
        )

        return PromptTemplate(
            name=name,
            version=version,
            template=template_text,
            variables=variables,
            examples=examples,
            metadata=metadata,
        )

    @staticmethod
    def extract_variables(
        template: str,
    ) -> list[str]:

        variables = re.findall(
            r"\{([^{}]+)\}",
            template,
        )

        return sorted(
            list(
                set(
                    variables,
                )
            )
        )
