from __future__ import annotations

from functools import lru_cache

import structlog
from app.ai.runtime.generation.structured_output.models import (
    OutputFormat,
)
from app.ai.runtime.generation.structured_output.parsers.json import (
    JsonParser,
)
from app.ai.runtime.generation.structured_output.parsers.markdown import (
    MarkdownParser,
)
from app.ai.runtime.generation.structured_output.parsers.pydantic import (
    PydanticParser,
)
from app.ai.runtime.generation.structured_output.parsers.xml import (
    XMLParser,
)
from app.ai.runtime.generation.structured_output.registry import (
    StructuredOutputRegistry,
)
from app.ai.runtime.generation.structured_output.service import (
    StructuredOutputService,
)

logger = structlog.get_logger()


###########################################################################
# Registry
###########################################################################


@lru_cache
def get_structured_output_registry() -> StructuredOutputRegistry:

    registry = StructuredOutputRegistry()

    registry.register(
        OutputFormat.JSON,
        JsonParser(),
    )

    registry.register(
        OutputFormat.PYDANTIC,
        PydanticParser(),
    )

    registry.register(
        OutputFormat.MARKDOWN,
        MarkdownParser(),
    )

    registry.register(
        OutputFormat.XML,
        XMLParser(),
    )

    logger.info(
        "structured_output.registry.initialized",
        formats=[fmt.value for fmt in registry.list_formats()],
    )

    return registry


###########################################################################
# Service
###########################################################################


@lru_cache
def get_structured_output_service() -> StructuredOutputService:

    logger.info(
        "structured_output.service.initialized",
    )

    return StructuredOutputService(
        registry=(get_structured_output_registry()),
    )
