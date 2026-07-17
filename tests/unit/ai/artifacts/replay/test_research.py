from __future__ import annotations

from uuid import uuid4

import pytest
from app.ai.artifacts.replay.research import ResearchReplayService


async def test_replay_raises_not_implemented() -> None:
    service = ResearchReplayService()

    with pytest.raises(NotImplementedError):
        await service.replay(uuid4())
