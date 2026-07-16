from __future__ import annotations

from typing import Any

from app.ai.runtime.generation.structured_output.interfaces import (
    OutputParserInterface,
)
from langchain_core.output_parsers import (
    PydanticOutputParser,
)
from pydantic import BaseModel


class PydanticParser(
    OutputParserInterface,
):
    async def parse(
        self,
        text: str,
        schema: type[BaseModel] | None = None,
    ) -> Any:

        if schema is None:
            raise ValueError("PydanticParser requires a schema.")

        parser: PydanticOutputParser[BaseModel] = PydanticOutputParser(
            pydantic_object=schema,
        )

        return parser.parse(
            text,
        )
