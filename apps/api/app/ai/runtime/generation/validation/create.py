from __future__ import annotations

from functools import lru_cache

import structlog
from app.ai.runtime.generation.validation.output.citation_validator import (
    CitationValidator,
)
from app.ai.runtime.generation.validation.output.schema_validator import (
    SchemaValidator,
)
from app.ai.runtime.generation.validation.service import (
    ValidationService,
)

logger = structlog.get_logger()


@lru_cache
def get_validation_service() -> ValidationService:

    service = ValidationService(
        validators=[
            SchemaValidator(),
            CitationValidator(),
        ],
    )

    logger.info(
        "validation.service.initialized",
        validators=service.validator_names,
    )

    return service
