from __future__ import annotations

from typing import Any

from app.ai.runtime.generation.structured_output.interfaces import (
    OutputParserInterface,
)
from langchain_core.output_parsers import (
    JsonOutputParser,
)
from pydantic import BaseModel


class JsonParser(
    OutputParserInterface,
):
    def __init__(
        self,
    ):
        self._parser = JsonOutputParser()

    async def parse(
        self,
        text: str,
        schema: type[BaseModel] | None = None,
    ) -> Any:

        return self._parser.parse(
            text,
        )
