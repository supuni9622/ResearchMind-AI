from app.ai.knowledge.context.formatter.enums import (
    PromptFormatStrategy,
)
from app.ai.knowledge.context.formatter.providers.agent import (
    AgentFormatterProvider,
)
from app.ai.knowledge.context.formatter.providers.default import (
    DefaultPromptFormatterProvider,
)
from app.ai.knowledge.context.formatter.providers.notebooklm import (
    NotebookLMFormatterProvider,
)
from app.ai.knowledge.context.formatter.providers.perplexity import (
    PerplexityFormatterProvider,
)
from app.ai.knowledge.context.formatter.providers.research import (
    ResearchFormatterProvider,
)
from app.ai.knowledge.context.formatter.registry import (
    PromptFormatterRegistry,
)
from app.ai.knowledge.context.formatter.service import (
    PromptFormatterService,
)


def create_prompt_formatter_service() -> PromptFormatterService:

    registry = PromptFormatterRegistry()

    registry.register(
        PromptFormatStrategy.DEFAULT,
        DefaultPromptFormatterProvider(),
    )

    registry.register(
        PromptFormatStrategy.NOTEBOOKLM,
        NotebookLMFormatterProvider(),
    )

    registry.register(
        PromptFormatStrategy.PERPLEXITY,
        PerplexityFormatterProvider(),
    )

    registry.register(
        PromptFormatStrategy.RESEARCH,
        ResearchFormatterProvider(),
    )

    registry.register(
        PromptFormatStrategy.AGENT,
        AgentFormatterProvider(),
    )

    return PromptFormatterService(
        registry=registry,
    )
