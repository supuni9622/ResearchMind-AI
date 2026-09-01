import uuid

import pytest
from app.models.project import Project
from app.models.research import ResearchConversation, ResearchSession
from app.models.user import User
from app.repositories.research import ResearchRepository


async def _make_owner(session) -> uuid.UUID:
    user = User(
        auth_provider="cognito",
        provider_user_id=str(uuid.uuid4()),
        email=f"{uuid.uuid4()}@example.com",
    )
    session.add(user)
    await session.flush()
    return user.id


async def _make_project(session, *, owner_id: uuid.UUID) -> uuid.UUID:
    project = Project(owner_id=owner_id, name="p")
    session.add(project)
    await session.flush()
    return project.id


def _make_conversation(
    *, owner_id: uuid.UUID, project_id: uuid.UUID | None = None
) -> ResearchConversation:
    return ResearchConversation(owner_id=owner_id, project_id=project_id, title="t")


def _make_research_session(
    *, owner_id: uuid.UUID, query: str = "How does RAG work?"
) -> ResearchSession:
    return ResearchSession(
        owner_id=owner_id,
        query=query,
        answer="RAG retrieves relevant context before generating an answer.",
        citations=[
            {"citation_id": "c1", "filename": "paper.pdf", "document_id": str(uuid.uuid4())}
        ],
        sources=[
            {
                "document_id": str(uuid.uuid4()),
                "filename": "paper.pdf",
                "chunk_id": str(uuid.uuid4()),
                "score": 0.9,
            }
        ],
        runtime_metadata={"provider": "groq", "model": "test-model"},
    )


@pytest.mark.asyncio
async def test_get_by_id_for_owner_returns_none_when_no_match(db_session) -> None:
    owner_id = await _make_owner(db_session)
    repository = ResearchRepository(db_session)

    result = await repository.get_by_id_for_owner(
        research_id=uuid.uuid4(),
        owner_id=owner_id,
    )

    assert result is None


@pytest.mark.asyncio
async def test_get_by_id_for_owner_returns_matching_session(db_session) -> None:
    owner_id = await _make_owner(db_session)
    repository = ResearchRepository(db_session)

    research_session = await repository.create(_make_research_session(owner_id=owner_id))

    result = await repository.get_by_id_for_owner(
        research_id=research_session.id,
        owner_id=owner_id,
    )

    assert result is not None
    assert result.id == research_session.id
    assert result.query == "How does RAG work?"
    assert result.citations[0]["citation_id"] == "c1"


@pytest.mark.asyncio
async def test_get_by_id_for_owner_never_returns_another_owners_session(db_session) -> None:
    owner_id = await _make_owner(db_session)
    other_owner_id = await _make_owner(db_session)
    repository = ResearchRepository(db_session)

    research_session = await repository.create(_make_research_session(owner_id=owner_id))

    result = await repository.get_by_id_for_owner(
        research_id=research_session.id,
        owner_id=other_owner_id,
    )

    assert result is None


@pytest.mark.asyncio
async def test_list_conversations_omits_project_conversations_by_default(db_session) -> None:
    """Omitting `project_id` means personal conversations only, not
    "every project" -- same contract as `ConversationRepository.
    list_conversations_page`."""

    owner_id = await _make_owner(db_session)
    project_id = await _make_project(db_session, owner_id=owner_id)
    repository = ResearchRepository(db_session)

    personal = await repository.create_conversation(_make_conversation(owner_id=owner_id))
    await repository.create_conversation(
        _make_conversation(owner_id=owner_id, project_id=project_id)
    )

    results = await repository.list_conversations_for_owner(owner_id=owner_id)

    assert [c.id for c in results] == [personal.id]


@pytest.mark.asyncio
async def test_list_conversations_scoped_to_a_project_excludes_personal_and_other_projects(
    db_session,
) -> None:
    owner_id = await _make_owner(db_session)
    project_id = await _make_project(db_session, owner_id=owner_id)
    other_project_id = await _make_project(db_session, owner_id=owner_id)
    repository = ResearchRepository(db_session)

    await repository.create_conversation(_make_conversation(owner_id=owner_id))
    in_project = await repository.create_conversation(
        _make_conversation(owner_id=owner_id, project_id=project_id)
    )
    await repository.create_conversation(
        _make_conversation(owner_id=owner_id, project_id=other_project_id)
    )

    results = await repository.list_conversations_for_owner(
        owner_id=owner_id, project_id=project_id
    )

    assert [c.id for c in results] == [in_project.id]
