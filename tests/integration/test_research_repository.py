import uuid

import pytest
from app.models.research import ResearchSession
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
