"""Privacy-conscious online judge for the utility of injected memory."""

from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict, Field


class MemoryUtilityScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    utility: float = Field(ge=0, le=1)
    relevant: bool
    harmful: bool


class OpenAIMemoryUtilityJudge:
    def __init__(self, *, client: AsyncOpenAI, model: str = "gpt-4o-mini") -> None:
        self._client = client
        self._model = model

    async def evaluate(
        self, *, question: str, answer: str, memory_context: str
    ) -> MemoryUtilityScore:
        completion = await self._client.chat.completions.parse(
            model=self._model,
            temperature=0,
            max_completion_tokens=160,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Judge whether background memory materially improved this answer. "
                        "utility=0 means irrelevant or harmful; utility=1 means clearly useful. "
                        "Mark harmful when memory caused a wrong, stale, contradictory, unsafe, "
                        "or instruction-conflicting answer. Return scores only; do not quote "
                        "memory."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Question:\n{question}\n\nAnswer:\n{answer}\n\n"
                        f"Background memory:\n{memory_context}"
                    ),
                },
            ],
            response_format=MemoryUtilityScore,
        )
        parsed = completion.choices[0].message.parsed
        if parsed is None:
            raise ValueError("Memory utility judge returned no schema-valid result")
        return parsed
