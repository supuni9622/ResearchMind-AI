from app.ai.knowledge.context.artifacts.create import (
    create_chunk_artifact_reader,
)
from app.ai.knowledge.context.builders.parent_expansion import (
    ParentExpansionService,
)
from app.ai.knowledge.context.compression.create import (
    create_compression_service,
)
from app.ai.knowledge.context.service import (
    ContextBuilderService,
)


def create_parent_expansion_service() -> ParentExpansionService:

    return ParentExpansionService(artifact_reader=(create_chunk_artifact_reader()))


def create_context_builder() -> ContextBuilderService:

    return ContextBuilderService(
        parent_expansion_service=(create_parent_expansion_service()),
        compression_service=(create_compression_service()),
    )
