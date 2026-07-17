from abc import ABC, abstractmethod

from app.ai.knowledge.context.models import (
    ContextResult,
)
from app.ai.knowledge.retrieval.models import (
    RetrievalResult,
)


class ContextBuilderInterface(ABC):
    @abstractmethod
    async def build(
        self,
        retrieval: RetrievalResult,
        query: str | None = None,
    ) -> ContextResult:
        pass
