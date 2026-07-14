from abc import (
    ABC,
    abstractmethod,
)

from app.ai.knowledge.context.citations.models import (
    CitationResult,
)
from app.ai.knowledge.context.models import (
    ContextChunk,
)


class CitationServiceInterface(
    ABC,
):
    @abstractmethod
    async def build(
        self,
        chunks: list[ContextChunk],
    ) -> CitationResult:
        pass
