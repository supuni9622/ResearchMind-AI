from app.ai.knowledge.context.compression.enums import (
    CompressionStrategy,
)
from app.ai.knowledge.context.compression.providers.embedding import (
    EmbeddingCompressionProvider,
)
from app.ai.knowledge.context.compression.providers.langchain import (
    LangChainCompressionProvider,
)
from app.ai.knowledge.context.compression.providers.llm import (
    LLMCompressionProvider,
)
from app.ai.knowledge.context.compression.providers.token_budget import (
    TokenBudgetCompressionProvider,
)
from app.ai.knowledge.context.compression.registry import (
    CompressionRegistry,
)
from app.ai.knowledge.context.compression.service import (
    CompressionService,
)


def create_compression_service() -> CompressionService:

    registry = CompressionRegistry()

    registry.register(
        CompressionStrategy.TOKEN_BUDGET,
        TokenBudgetCompressionProvider(),
    )

    registry.register(
        CompressionStrategy.EMBEDDING_REDUNDANCY,
        EmbeddingCompressionProvider(),
    )

    registry.register(
        CompressionStrategy.LANGCHAIN_CONTEXTUAL,
        LangChainCompressionProvider(),
    )

    registry.register(
        CompressionStrategy.LLM,
        LLMCompressionProvider(),
    )

    return CompressionService(
        registry=registry,
    )
