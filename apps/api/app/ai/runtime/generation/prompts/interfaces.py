from __future__ import annotations

from abc import ABC, abstractmethod

from app.ai.runtime.generation.prompts.models import (
    PromptRenderRequest,
    PromptRenderResult,
    PromptTemplate,
)


class PromptRegistryInterface(
    ABC,
):
    @abstractmethod
    def register(
        self,
        template: PromptTemplate,
    ) -> None:
        pass

    @abstractmethod
    def get(
        self,
        name: str,
        version: str | None = None,
    ) -> PromptTemplate:
        pass


class PromptServiceInterface(
    ABC,
):
    @abstractmethod
    async def render(
        self,
        request: PromptRenderRequest,
    ) -> PromptRenderResult:
        pass
