"""
`MemoryService.remember_extracted()` -- exact-duplicate dedup (pre-existing)
plus the preference-supersession tier added as a Wave 2 staleness fix
(`docs/todo/user-memory-profile-injection-gap.md` "Resolution" section).
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import ANY, AsyncMock
from uuid import uuid4

import pytest
from app.ai.memory.enums import MemoryScopeType, MemoryType
from app.ai.memory.models import MemoryRecord
from app.ai.memory.policy.models import PreferenceTopicClassification
from app.ai.memory.policy.supersession import PreferenceSupersessionMatch
from app.ai.memory.services.memory_service import MemoryService
from app.core.settings import settings


def _record(content: str, *, importance: float = 0.5) -> MemoryRecord:
    now = datetime.now(UTC)
    return MemoryRecord(
        id=uuid4(),
        owner_id=uuid4(),
        type=MemoryType.USER,
        content=content,
        importance_score=importance,
        created_at=now,
        updated_at=now,
    )


def _service(
    *,
    user: AsyncMock | None = None,
    supersession: AsyncMock | None = None,
) -> MemoryService:
    return MemoryService(
        session_memory=AsyncMock(),
        user_memory=user or AsyncMock(),
        semantic_memory=AsyncMock(),
        research_memory=AsyncMock(),
        supersession_service=supersession,
    )


@pytest.mark.asyncio
async def test_exact_duplicate_updates_provenance_without_checking_supersession() -> None:
    existing = _record("prefers concise answers")
    user = AsyncMock()
    user.find_exact_content = AsyncMock(return_value=existing)
    user.update = AsyncMock(return_value=existing)
    supersession = AsyncMock()
    service = _service(user=user, supersession=supersession)

    record, status = await service.remember_extracted(
        owner_id=uuid4(),
        type=MemoryType.USER,
        content="prefers concise answers",
        importance_score=0.6,
        metadata={},
    )

    assert status == "duplicate"
    assert record is existing
    supersession.find_superseded.assert_not_awaited()


@pytest.mark.asyncio
async def test_supersedes_an_existing_preference_on_the_same_topic() -> None:
    owner_id = uuid4()
    old = _record("prefers concise answers")
    user = AsyncMock()
    user.find_exact_content = AsyncMock(return_value=None)
    user.find_preference_candidates = AsyncMock(return_value=[old])
    user.update = AsyncMock(
        return_value=old.model_copy(update={"content": "prefers detailed answers"})
    )
    supersession = AsyncMock()
    supersession.classify_topic = AsyncMock(
        return_value=PreferenceTopicClassification(
            preference_key="response_length", search_terms=["answers"]
        )
    )
    supersession.find_superseded = AsyncMock(
        return_value=PreferenceSupersessionMatch(record=old, reason="same topic")
    )
    service = _service(user=user, supersession=supersession)

    record, status = await service.remember_extracted(
        owner_id=owner_id,
        type=MemoryType.USER,
        content="prefers detailed answers",
        importance_score=0.7,
        metadata={"source": "feedback"},
    )

    assert status == "superseded"
    assert record is not None
    assert record.content == "prefers detailed answers"
    user.find_preference_candidates.assert_awaited_once_with(
        owner_id=owner_id,
        scope_type=MemoryScopeType.PERSONAL,
        project_id=None,
        preference_key="response_length",
        search_terms=["answers"],
        limit=settings.memory_preference_candidate_limit,
    )
    user.update.assert_awaited_once_with(
        owner_id=owner_id,
        memory_id=old.id,
        scope_type=MemoryScopeType.PERSONAL,
        project_id=None,
        content="prefers detailed answers",
        metadata={
            "source": "feedback",
            "preference_key": "response_length",
            "_supersession": {
                "replaced_memory_id": str(old.id),
                "reason": "same topic",
                "decided_at": ANY,
            },
        },
        importance_score=0.7,
    )


@pytest.mark.asyncio
async def test_no_supersession_match_falls_through_to_plain_create() -> None:
    user = AsyncMock()
    user.find_exact_content = AsyncMock(return_value=None)
    user.find_preference_candidates = AsyncMock(return_value=[_record("prefers Claude")])
    created = _record("is researching graph databases")
    user.remember = AsyncMock(return_value=created)
    supersession = AsyncMock()
    supersession.classify_topic = AsyncMock(return_value=None)
    supersession.classify_topic = AsyncMock(
        return_value=PreferenceTopicClassification(
            preference_key="research_topic", search_terms=["graph databases"]
        )
    )
    supersession.find_superseded = AsyncMock(return_value=None)
    service = _service(user=user, supersession=supersession)

    record, status = await service.remember_extracted(
        owner_id=uuid4(),
        type=MemoryType.USER,
        content="is researching graph databases",
        importance_score=0.7,
        metadata={},
    )

    assert status == "created"
    assert record is created


@pytest.mark.asyncio
async def test_dormant_project_preference_is_nominated_without_recent_list_scan() -> None:
    owner_id = uuid4()
    project_id = uuid4()
    dormant = _record("prefers concise project reports")
    user = AsyncMock()
    user.find_exact_content = AsyncMock(return_value=None)
    user.find_preference_candidates = AsyncMock(return_value=[dormant])
    user.update = AsyncMock(return_value=dormant)
    supersession = AsyncMock()
    supersession.classify_topic = AsyncMock(
        return_value=PreferenceTopicClassification(
            preference_key="response_length", search_terms=["project reports"]
        )
    )
    supersession.find_superseded = AsyncMock(
        return_value=PreferenceSupersessionMatch(record=dormant, reason="same scoped topic")
    )
    service = _service(user=user, supersession=supersession)

    _, status = await service.remember_extracted(
        owner_id=owner_id,
        scope_type=MemoryScopeType.PROJECT,
        project_id=project_id,
        type=MemoryType.USER,
        content="prefers detailed project reports",
        importance_score=0.8,
        metadata={},
    )

    assert status == "superseded"
    user.find_preference_candidates.assert_awaited_once_with(
        owner_id=owner_id,
        scope_type=MemoryScopeType.PROJECT,
        project_id=project_id,
        preference_key="response_length",
        search_terms=["project reports"],
        limit=settings.memory_preference_candidate_limit,
    )
    user.list_preferences.assert_not_awaited()


@pytest.mark.asyncio
async def test_research_type_never_checks_supersession() -> None:
    """RESEARCH findings are additive facts, not preferences that flip --
    supersession is USER-only."""

    research = AsyncMock()
    research.find_exact_content = AsyncMock(return_value=None)
    created = _record("evidence: benchmark X outperforms Y")
    research.remember = AsyncMock(return_value=created)
    supersession = AsyncMock()
    supersession.classify_topic = AsyncMock(return_value=None)
    service = MemoryService(
        session_memory=AsyncMock(),
        user_memory=AsyncMock(),
        semantic_memory=AsyncMock(),
        research_memory=research,
        supersession_service=supersession,
    )

    record, status = await service.remember_extracted(
        owner_id=uuid4(),
        type=MemoryType.RESEARCH,
        content="evidence: benchmark X outperforms Y",
        importance_score=0.7,
        metadata={},
    )

    assert status == "created"
    supersession.find_superseded.assert_not_awaited()


@pytest.mark.asyncio
async def test_supersession_check_failure_falls_through_to_plain_create() -> None:
    """A broken supersession check must never block the write itself."""

    user = AsyncMock()
    user.find_exact_content = AsyncMock(return_value=None)
    user.list_preferences = AsyncMock(side_effect=RuntimeError("db unavailable"))
    created = _record("prefers dark mode")
    user.remember = AsyncMock(return_value=created)
    supersession = AsyncMock()
    supersession.classify_topic = AsyncMock(return_value=None)
    service = _service(user=user, supersession=supersession)

    record, status = await service.remember_extracted(
        owner_id=uuid4(),
        type=MemoryType.USER,
        content="prefers dark mode",
        importance_score=0.7,
        metadata={},
    )

    assert status == "created"
    assert record is created


@pytest.mark.asyncio
async def test_disabled_via_settings_skips_the_supersession_check_entirely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "memory_preference_supersession_enabled", False)
    user = AsyncMock()
    user.find_exact_content = AsyncMock(return_value=None)
    created = _record("prefers dark mode")
    user.remember = AsyncMock(return_value=created)
    supersession = AsyncMock()
    service = _service(user=user, supersession=supersession)

    record, status = await service.remember_extracted(
        owner_id=uuid4(),
        type=MemoryType.USER,
        content="prefers dark mode",
        importance_score=0.7,
        metadata={},
    )

    assert status == "created"
    assert record is created
    supersession.find_superseded.assert_not_awaited()
    user.list_preferences.assert_not_awaited()
