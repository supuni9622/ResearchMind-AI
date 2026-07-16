from __future__ import annotations

import re
from typing import Any

import structlog
from app.ai.runtime.generation.prompts.interfaces import (
    PromptServiceInterface,
)
from app.ai.runtime.generation.prompts.langchain.prompt_factory import (
    PromptFactory,
)
from app.ai.runtime.generation.prompts.models import (
    PromptRenderRequest,
    PromptRenderResult,
    PromptTemplate,
)
from app.ai.runtime.generation.prompts.registry import (
    PromptRegistry,
)
from langchain_core.messages import BaseMessage

logger = structlog.get_logger()


class PromptService(
    PromptServiceInterface,
):
    def __init__(
        self,
        registry: PromptRegistry,
    ) -> None:
        self._registry = registry

    # ==========================================================
    # Public API
    # ==========================================================

    async def render(
        self,
        request: PromptRenderRequest,
    ) -> PromptRenderResult:

        template = self._registry.get(
            request.template_name,
            request.version,
        )

        messages = await self.render_messages(
            request,
        )

        rendered_prompt = self._messages_to_text(
            messages,
        )

        estimated_tokens = self.estimate_tokens(
            rendered_prompt,
        )

        logger.debug(
            "prompt.rendered",
            template=request.template_name,
            version=template.version,
            estimated_tokens=estimated_tokens,
        )

        return PromptRenderResult(
            template_name=template.name,
            version=template.version,
            rendered_prompt=rendered_prompt,
            estimated_tokens=estimated_tokens,
            metadata=template.metadata,
        )

    async def render_text(
        self,
        request: PromptRenderRequest,
    ) -> str:

        result = await self.render(
            request,
        )

        return result.rendered_prompt

    async def render_messages(
        self,
        request: PromptRenderRequest,
    ) -> list[BaseMessage]:

        template = self._registry.get(
            request.template_name,
            request.version,
        )

        self._validate_variables(
            template,
            request.variables,
        )

        examples = request.examples or template.examples

        prompt = PromptFactory.build(
            template,
            examples,
        )

        rendered = prompt.invoke(
            request.variables,
        )

        return rendered.to_messages()

    # ==========================================================
    # Validation
    # ==========================================================

    def _validate_variables(
        self,
        template: PromptTemplate,
        supplied_variables: dict[
            str,
            Any,
        ],
    ) -> None:

        missing = [
            variable for variable in template.variables if variable not in supplied_variables
        ]

        if missing:
            logger.error(
                "prompt.variables_missing",
                template=template.name,
                version=template.version,
                missing=missing,
            )

            raise ValueError(
                f"Missing prompt variables for {template.name}:{template.version}: {missing}"
            )

    # ==========================================================
    # Rendering Helpers
    # ==========================================================

    def _messages_to_text(
        self,
        messages: list[BaseMessage],
    ) -> str:

        parts: list[str] = []

        for message in messages:
            content = message.content

            if not content:
                continue

            parts.append(
                str(
                    content,
                )
            )

        return "\n\n".join(
            parts,
        )

    # ==========================================================
    # Token Estimation
    # ==========================================================

    def estimate_tokens(
        self,
        text: str,
    ) -> int:
        """
        Rough estimate.

        Future:
        - tiktoken
        - LangChain token counters
        - provider tokenizers
        """

        words = re.findall(
            r"\S+",
            text,
        )

        return int(len(words) * 1.3)

    # ==========================================================
    # Registry Helpers
    # ==========================================================

    def get_template(
        self,
        name: str,
        version: str | None = None,
    ) -> PromptTemplate:

        return self._registry.get(
            name,
            version,
        )

    def exists(
        self,
        name: str,
        version: str | None = None,
    ) -> bool:

        return self._registry.exists(
            name,
            version,
        )

    def list_templates(
        self,
    ) -> list[str]:

        return self._registry.list_names()

    def versions(
        self,
        name: str,
    ) -> list[str]:

        return self._registry.versions(
            name,
        )
