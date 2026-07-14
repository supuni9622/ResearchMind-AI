from app.ai.knowledge.context.formatter.interfaces import (
    PromptFormatterProvider,
)
from app.ai.knowledge.context.formatter.models import (
    PromptFormattingResult,
)
from app.ai.knowledge.context.models import (
    PromptContext,
)


class PerplexityFormatterProvider(
    PromptFormatterProvider,
):
    async def format(
        self,
        context: PromptContext,
    ) -> PromptFormattingResult:

        sections: list[str] = []

        for chunk in context.chunks:
            citation = chunk.citation_id or "UNKNOWN"

            content = chunk.content.replace("\n", " ")

            if len(content) > 1000:
                content = content[:1000] + "..."

            section = f"""
Evidence [{citation}]

Document:
{chunk.filename}

Key Evidence:

{content}
"""

            sections.append(section.strip())

        return PromptFormattingResult(formatted_context="\n\n".join(sections))
