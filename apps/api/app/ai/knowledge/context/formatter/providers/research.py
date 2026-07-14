from collections import defaultdict

from app.ai.knowledge.context.formatter.interfaces import (
    PromptFormatterProvider,
)
from app.ai.knowledge.context.formatter.models import (
    PromptFormattingResult,
)
from app.ai.knowledge.context.models import (
    PromptContext,
)


class ResearchFormatterProvider(
    PromptFormatterProvider,
):
    async def format(
        self,
        context: PromptContext,
    ) -> PromptFormattingResult:

        grouped: dict[
            str,
            list[str],
        ] = defaultdict(list)

        for chunk in context.chunks:
            topic = chunk.heading or chunk.filename

            citation = chunk.citation_id or "UNKNOWN"

            grouped[topic].append(
                f"""
Source:
{citation}

Document:
{chunk.filename}

Content:

{chunk.content}
"""
            )

        sections = []

        for (
            topic,
            chunks,
        ) in grouped.items():
            section = f"""
==================================================
TOPIC:

{topic}

{"".join(chunks)}

==================================================
"""

            sections.append(section.strip())

        return PromptFormattingResult(formatted_context="\n\n".join(sections))
