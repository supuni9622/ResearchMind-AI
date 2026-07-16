from __future__ import annotations

from app.ai.runtime.generation.structured_output.interfaces import (
    OutputParserInterface,
)
from app.ai.runtime.generation.structured_output.models import (
    OutputFormat,
)


class StructuredOutputRegistry:
    def __init__(
        self,
    ) -> None:

        self._parsers: dict[
            OutputFormat,
            OutputParserInterface,
        ] = {}

    def register(
        self,
        output_format: OutputFormat,
        parser: OutputParserInterface,
    ) -> None:

        self._parsers[output_format] = parser

    def get(
        self,
        output_format: OutputFormat,
    ) -> OutputParserInterface:

        parser = self._parsers.get(
            output_format,
        )

        if parser is None:
            raise ValueError(f"No parser registered for {output_format}")

        return parser

    def exists(
        self,
        output_format: OutputFormat,
    ) -> bool:

        return output_format in self._parsers

    def list_formats(
        self,
    ) -> list[OutputFormat]:

        return list(
            self._parsers.keys(),
        )
