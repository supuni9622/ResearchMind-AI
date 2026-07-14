from app.ai.knowledge.context.formatter.interfaces import (
    PromptFormatterProvider,
)
from app.ai.knowledge.context.formatter.models import (
    PromptFormattingResult,
)
from app.ai.knowledge.context.models import (
    PromptContext,
)


class DefaultPromptFormatterProvider(
    PromptFormatterProvider,
):
    """
    NotebookLM style formatting.
    """

    async def format(
        self,
        context: PromptContext,
    ) -> PromptFormattingResult:

        sections: list[str] = []

        for chunk in context.chunks:
            citation = chunk.citation_id or "UNKNOWN"

            pages = ""

            if chunk.page_numbers:
                pages = ", ".join(str(page) for page in (chunk.page_numbers))

            section = f"""
==================================================
Source: {citation}

Document:
{chunk.filename}
"""

            if chunk.heading:
                section += f"""

Heading:
{chunk.heading}
"""

            if pages:
                section += f"""

Pages:
{pages}
"""

            if chunk.parent_content:
                section += f"""

Parent Context:

{chunk.parent_content}
"""

            section += f"""

Content:

{chunk.content}
"""

            sections.append(section.strip())

        return PromptFormattingResult(formatted_context="\n\n".join(sections))
