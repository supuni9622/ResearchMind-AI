from __future__ import annotations

import re
from typing import Any

from app.ai.runtime.generation.structured_output.interfaces import (
    OutputParserInterface,
)
from pydantic import BaseModel


class MarkdownParser(
    OutputParserInterface,
):
    async def parse(
        self,
        text: str,
        schema: type[BaseModel] | None = None,
    ) -> Any:

        sections = {}

        matches = re.split(
            r"^##\s+",
            text,
            flags=re.MULTILINE,
        )

        for section in matches:
            section = section.strip()

            if not section:
                continue

            lines = section.splitlines()

            title = lines[0]

            content = "\n".join(lines[1:])

            sections[title] = content

        return sections
