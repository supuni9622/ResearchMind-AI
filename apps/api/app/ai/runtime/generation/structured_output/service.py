from __future__ import annotations

import structlog
from app.ai.runtime.generation.structured_output.models import (
    OutputFormat,
    StructuredOutputRequest,
    StructuredOutputResult,
)
from app.ai.runtime.generation.structured_output.registry import (
    StructuredOutputRegistry,
)
from app.ai.runtime.generation.structured_output.repair import (
    StructuredOutputRepair,
)
from pydantic import BaseModel

logger = structlog.get_logger()


class StructuredOutputService:
    def __init__(
        self,
        registry: StructuredOutputRegistry,
    ) -> None:
        self._registry = registry

    ####################################################################
    # Public
    ####################################################################

    async def parse(
        self,
        request: StructuredOutputRequest,
    ) -> StructuredOutputResult:

        try:
            parsed = await self._parse(
                request,
            )

            return StructuredOutputResult(
                raw_content=request.content,
                parsed_content=parsed,
                success=True,
            )

        except Exception as exc:
            logger.exception(
                "structured_output.parse_failed",
                output_format=request.output_format.value,
            )

            return StructuredOutputResult(
                raw_content=request.content,
                parsed_content=None,
                success=False,
                errors=[
                    str(exc),
                ],
            )

    ####################################################################
    # Internal
    ####################################################################

    async def _parse(
        self,
        request: StructuredOutputRequest,
    ):

        parser = self._registry.get(
            request.output_format,
        )

        content = request.content

        #
        # JSON repair
        #

        if request.repair_json and request.output_format in {
            OutputFormat.JSON,
            OutputFormat.PYDANTIC,
        }:
            content = StructuredOutputRepair.clean(
                content,
            )

        #
        # Pydantic requires schema
        #

        if request.output_format == OutputFormat.PYDANTIC:
            if request.output_schema is None:
                raise ValueError("PYDANTIC output format requires a schema.")

            return await parser.parse(
                content,
                request.output_schema,
            )

        #
        # Other parsers
        #

        return await parser.parse(
            content,
        )

    ####################################################################
    # Convenience APIs
    ####################################################################

    async def parse_json(
        self,
        text: str,
    ):

        return await self.parse(
            StructuredOutputRequest(
                content=text,
                output_format=OutputFormat.JSON,
            )
        )

    async def parse_pydantic(
        self,
        text: str,
        schema: type[BaseModel],
    ):

        return await self.parse(
            StructuredOutputRequest(
                content=text,
                output_format=OutputFormat.PYDANTIC,
                output_schema=schema,
            )
        )

    async def parse_markdown(
        self,
        text: str,
    ):

        return await self.parse(
            StructuredOutputRequest(
                content=text,
                output_format=OutputFormat.MARKDOWN,
            )
        )

    async def parse_xml(
        self,
        text: str,
    ):

        return await self.parse(
            StructuredOutputRequest(
                content=text,
                output_format=OutputFormat.XML,
            )
        )
