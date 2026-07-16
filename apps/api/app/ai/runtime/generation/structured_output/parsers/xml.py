from __future__ import annotations

from typing import Any

import xmltodict
from app.ai.runtime.generation.structured_output.interfaces import (
    OutputParserInterface,
)
from pydantic import BaseModel


class XMLParser(
    OutputParserInterface,
):
    async def parse(
        self,
        text: str,
        schema: type[BaseModel] | None = None,
    ) -> Any:

        return xmltodict.parse(
            text,
        )
