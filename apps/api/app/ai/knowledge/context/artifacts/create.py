from app.ai.knowledge.context.artifacts.reader import (
    ChunkArtifactReader,
)
from app.core.settings import (
    settings,
)
from app.infrastructure.storage.factory import (
    create_storage,
)


def create_chunk_artifact_reader() -> ChunkArtifactReader:

    return ChunkArtifactReader(
        storage=create_storage(
            settings,
        )
    )
