from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.research import ResearchSession


class ResearchRepository:
    """
    Repository responsible for ResearchSession persistence.

    This class contains only database operations.

    It must never:
        - contain business logic
        - call external services
        - commit or rollback transactions
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        research_session: ResearchSession,
    ) -> ResearchSession:
        """
        Persist a new research session.

        The transaction is not committed here.
        """

        self.session.add(research_session)

        await self.session.flush()
        await self.session.refresh(research_session)

        return research_session

    async def get_by_id_for_owner(
        self,
        *,
        research_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> ResearchSession | None:
        """
        Retrieve a research session by primary key, scoped to its owner so
        a caller can never load another user's research session by id.
        """

        statement = select(ResearchSession).where(
            ResearchSession.id == research_id,
            ResearchSession.owner_id == owner_id,
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()
