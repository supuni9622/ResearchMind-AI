from __future__ import annotations

from pathlib import Path

import structlog
from app.ai.runtime.generation.prompts.builder import (
    PromptBuilder,
)
from app.ai.runtime.generation.prompts.interfaces import (
    PromptRegistryInterface,
)
from app.ai.runtime.generation.prompts.models import (
    PromptTemplate,
)

logger = structlog.get_logger()


class PromptRegistry(
    PromptRegistryInterface,
):
    """
    Canonical registry for all prompt templates.

    Structure:

    {
        "research": {
            "v1": PromptTemplate,
            "v2": PromptTemplate,
        },
        "chat": {
            "v1": PromptTemplate,
            "v2": PromptTemplate,
        }
    }
    """

    def __init__(
        self,
    ) -> None:
        self._templates: dict[
            str,
            dict[str, PromptTemplate],
        ] = {}

    # ==========================================================
    # Registration
    # ==========================================================

    def register(
        self,
        template: PromptTemplate,
    ) -> None:

        versions = self._templates.setdefault(
            template.name,
            {},
        )

        versions[template.version] = template

        logger.info(
            "prompt.registered",
            name=template.name,
            version=template.version,
        )

    def register_directory(
        self,
        directory: Path,
    ) -> None:
        """
        Register a single prompt directory.

        Example:

        templates/research/v1/
        """

        template = PromptBuilder.build_from_directory(
            directory,
        )

        self.register(
            template,
        )

    def register_all(
        self,
        root_directory: Path,
    ) -> None:
        """
        Recursively register all prompts.

        Structure:

        templates/

            research/
                v1/
                v2/

            chat/
                v1/
                v2/
        """

        if not root_directory.exists():
            logger.warning(
                "prompt.root_directory_missing",
                path=str(
                    root_directory,
                ),
            )

            return

        for prompt_type in root_directory.iterdir():
            if not (prompt_type.is_dir()):
                continue

            for version_dir in prompt_type.iterdir():
                if not (version_dir.is_dir()):
                    continue

                try:
                    self.register_directory(
                        version_dir,
                    )

                except Exception:
                    logger.exception(
                        "prompt.registration_failed",
                        path=str(
                            version_dir,
                        ),
                    )

    # ==========================================================
    # Retrieval
    # ==========================================================

    def get(
        self,
        name: str,
        version: str | None = None,
    ) -> PromptTemplate:

        if name not in self._templates:
            raise ValueError(f"Prompt '{name}' not found.")

        versions = self._templates[name]

        #
        # specific version
        #

        if version:
            if version not in versions:
                raise ValueError(f"Prompt '{name}:{version}' not found.")

            return versions[version]

        #
        # latest version
        #

        latest = self.latest_version(
            name,
        )

        return versions[latest]

    # ==========================================================
    # Utilities
    # ==========================================================

    def exists(
        self,
        name: str,
        version: str | None = None,
    ) -> bool:

        if name not in self._templates:
            return False

        if version is None:
            return True

        return version in self._templates[name]

    def list_names(
        self,
    ) -> list[str]:

        return sorted(
            self._templates.keys(),
        )

    def versions(
        self,
        name: str,
    ) -> list[str]:

        if name not in self._templates:
            return []

        return sorted(
            self._templates[name].keys(),
        )

    def latest_version(
        self,
        name: str,
    ) -> str:

        versions = self.versions(
            name,
        )

        if not versions:
            raise ValueError(f"Prompt '{name}' not found.")

        #
        # v1,v2,v3 sorting
        #

        return sorted(
            versions,
            key=lambda x: int(
                x.removeprefix(
                    "v",
                )
            ),
        )[-1]

    # ==========================================================
    # Metadata Helpers
    # ==========================================================

    def metadata(
        self,
        name: str,
        version: str | None = None,
    ):

        template = self.get(
            name,
            version,
        )

        return template.metadata

    def preferred_providers(
        self,
        name: str,
        version: str | None = None,
    ):

        metadata = self.metadata(
            name,
            version,
        )

        return metadata.preferred_providers

    # ==========================================================
    # Diagnostics
    # ==========================================================

    def total_prompts(
        self,
    ) -> int:

        count = 0

        for versions in self._templates.values():
            count += len(
                versions,
            )

        return count

    def dump(
        self,
    ) -> dict[
        str,
        list[str],
    ]:

        result: dict[
            str,
            list[str],
        ] = {}

        for (
            name,
            versions,
        ) in self._templates.items():
            result[name] = sorted(
                versions.keys(),
            )

        return result
