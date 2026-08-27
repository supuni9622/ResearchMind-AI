from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from app.ai.memory.extraction.models import ExtractedMemoryBatch
from app.ai.memory.extraction.service import MemoryExtractionService
from app.core.settings import settings


@pytest.mark.asyncio
async def test_extraction_output_is_capped_per_turn() -> None:
    runtime = AsyncMock()
    runtime.execute = AsyncMock(
        return_value=SimpleNamespace(
            parsed_output=ExtractedMemoryBatch.model_validate(
                {
                    "memories": [
                        {"content": f"preference {index}", "type": "user", "importance": 0.8}
                        for index in range(settings.memory_extraction_max_memories_per_turn + 3)
                    ]
                }
            )
        )
    )

    extracted = await MemoryExtractionService(runtime).extract(
        user_message="Remember several durable preferences",
        assistant_message="Noted",
    )

    assert len(extracted) == settings.memory_extraction_max_memories_per_turn
