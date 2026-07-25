"""Provider interface for the Research Intelligence MCP paper-search platform.

Providers must return canonical models only, never expose raw MCP result
objects, and translate provider errors into
`app.ai.tools.paper_search.exceptions` before returning (mirrors
`app.ai.tools.web_search.interfaces`).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.ai.tools.paper_search.models import PaperSearchRequest, PaperSearchResult


class PaperSearchProviderInterface(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    async def search(self, request: PaperSearchRequest) -> PaperSearchResult:
        raise NotImplementedError
