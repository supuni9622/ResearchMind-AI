from pydantic import (
    BaseModel,
    ConfigDict,
)


class PromptFormattingResult(
    BaseModel,
):
    model_config = ConfigDict(
        extra="forbid",
    )

    formatted_context: str
