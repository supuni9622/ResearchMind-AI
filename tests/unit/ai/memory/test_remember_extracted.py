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
from app.ai.memory.policy.models import (
    PreferenceKind,
    PreferenceTopicClassification,
    PreferenceValueType,
)
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


def test_typed_preference_metadata_coerces_boolean_values() -> None:
    metadata = MemoryService._with_typed_preference_metadata(
        {"source": "feedback"},
        PreferenceTopicClassification(
            preference_key="preferred_tool",
            preference_kind=PreferenceKind.PREFERRED_TOOL,
            normalized_value="enabled",
            value_type=PreferenceValueType.BOOLEAN,
            confidence=0.91,
            explicit=True,
            search_terms=["tool"],
        ),
    )

    assert metadata["preference"]["value"] is True
    assert metadata["preference"]["value_type"] == "boolean"


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
            preference_key="response_length",
            preference_kind=PreferenceKind.RESPONSE_LENGTH,
            normalized_value="detailed",
            value_type=PreferenceValueType.STRING,
            confidence=0.96,
            explicit=True,
            search_terms=["answers"],
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
            "preference": {
                "schema_version": "v1",
                "kind": "response_length",
                "key": "response_length",
                "value": "detailed",
                "value_type": "string",
                "confidence": 0.96,
                "explicit": True,
                "source": "feedback",
                "effective_at": ANY,
                "provenance": {},
            },
            "_supersession": {
                "replaced_memory_id": str(old.id),
                "reason": "same topic",
                "decided_at": ANY,
            },
        },
        importance_score=0.7,
    )


@pytest.mark.asyncio
async def test_typed_controlled_preference_supersedes_without_second_judge_call() -> None:
    owner_id = uuid4()
    old = _record("prefers concise answers").model_copy(
        update={
            "metadata": {
                "preference_key": "response_length",
                "preference": {
                    "schema_version": "v1",
                    "key": "response_length",
                    "value": "concise",
                },
            }
        }
    )
    user = AsyncMock()
    user.find_exact_content = AsyncMock(return_value=None)
    user.find_preference_candidates = AsyncMock(return_value=[old])
    user.update = AsyncMock(return_value=old)
    supersession = AsyncMock()
    supersession.classify_topic = AsyncMock(
        return_value=PreferenceTopicClassification(
            preference_key="response_length",
            preference_kind=PreferenceKind.RESPONSE_LENGTH,
            normalized_value="detailed",
            value_type=PreferenceValueType.STRING,
            confidence=0.97,
            explicit=True,
            search_terms=["answers"],
        )
    )
    service = _service(user=user, supersession=supersession)

    _, status = await service.remember_extracted(
        owner_id=owner_id,
        type=MemoryType.USER,
        content="prefer detailed answers",
        importance_score=0.8,
        metadata={"source": "extraction", "conversation_id": "conversation-1"},
    )

    assert status == "superseded"
    supersession.find_superseded.assert_not_awaited()
    update_metadata = user.update.await_args.kwargs["metadata"]
    assert update_metadata["preference"]["value"] == "detailed"
    assert update_metadata["preference"]["provenance"] == {"conversation_id": "conversation-1"}
    assert update_metadata["_supersession"]["reason"] == (
        "deterministic_typed_preference_key_match"
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
            preference_key="research_topic",
            preference_kind=PreferenceKind.CUSTOM,
            normalized_value="graph databases",
            value_type=PreferenceValueType.STRING,
            confidence=0.8,
            explicit=False,
            search_terms=["graph databases"],
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
    remembered_metadata = user.remember.await_args.kwargs["metadata"]
    assert remembered_metadata["preference_key"] == "research_topic"
    assert remembered_metadata["preference"] == {
        "schema_version": "v1",
        "kind": "custom",
        "key": "research_topic",
        "value": "graph databases",
        "value_type": "string",
        "confidence": 0.8,
        "explicit": False,
        "source": "extraction",
        "effective_at": ANY,
        "provenance": {},
    }


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
            preference_key="response_length",
            preference_kind=PreferenceKind.RESPONSE_LENGTH,
            normalized_value="detailed",
            value_type=PreferenceValueType.STRING,
            confidence=0.96,
            explicit=True,
            search_terms=["project reports"],
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
