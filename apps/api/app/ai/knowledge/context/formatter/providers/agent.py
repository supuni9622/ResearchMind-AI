from app.ai.knowledge.context.formatter.interfaces import (
    PromptFormatterProvider,
)
from app.ai.knowledge.context.formatter.models import (
    PromptFormattingResult,
)
from app.ai.knowledge.context.models import (
    PromptContext,
)


class AgentFormatterProvider(
    PromptFormatterProvider,
):
    async def format(
        self,
        context: PromptContext,
    ) -> PromptFormattingResult:

        facts = []

        evidence = []

        for chunk in context.chunks:
            citation = chunk.citation_id or "UNKNOWN"

            text = chunk.content.replace("\n", " ")

            if len(text) > 500:
                text = text[:500] + "..."

            facts.append(f"- {text}")

            evidence.append(f"[{citation}] {chunk.filename}")

        formatted = f"""
FACTS

{chr(10).join(facts)}

==================================================

EVIDENCE

{chr(10).join(evidence)}
"""

        return PromptFormattingResult(formatted_context=formatted)
