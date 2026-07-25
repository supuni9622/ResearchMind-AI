"""Provider interface for the Web Search Tool Platform (PRD §10).

Providers must return canonical models only, never expose SDK response
objects, and translate provider errors into
`app.ai.tools.web_search.exceptions` before returning.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.ai.tools.web_search.models import WebSearchRequest, WebSearchResult


class WebSearchProviderInterface(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    async def search(self, request: WebSearchRequest) -> WebSearchResult:
        raise NotImplementedError
