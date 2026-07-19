from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.research import ResearchConversation, ResearchSession


class ResearchRepository:
    """
    Repository responsible for ResearchSession/ResearchConversation
    persistence.

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

    # -- ResearchConversation --------------------------------------------

    async def create_conversation(
        self,
        conversation: ResearchConversation,
    ) -> ResearchConversation:
        """
        Persist a new research conversation.

        The transaction is not committed here.
        """

        self.session.add(conversation)

        await self.session.flush()
        await self.session.refresh(conversation)

        return conversation

    async def get_conversation_by_id_for_owner(
        self,
        *,
        conversation_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> ResearchConversation | None:
        """
        Retrieve a research conversation by primary key, scoped to its
        owner so a caller can never load another user's conversation by
        id.
        """

        statement = select(ResearchConversation).where(
            ResearchConversation.id == conversation_id,
            ResearchConversation.owner_id == owner_id,
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def list_conversations_for_owner(
        self,
        *,
        owner_id: uuid.UUID,
        limit: int = 50,
    ) -> list[ResearchConversation]:
        """
        Most recently updated `limit` conversations for `owner_id`, newest
        first -- the shape a "History" sidebar needs.
        """

        statement = (
            select(ResearchConversation)
            .where(ResearchConversation.owner_id == owner_id)
            .order_by(ResearchConversation.updated_at.desc())
            .limit(limit)
        )

        result = await self.session.execute(statement)

        return list(result.scalars().all())

    async def list_sessions_for_conversation(
        self,
        *,
        conversation_id: uuid.UUID,
        owner_id: uuid.UUID,
        limit: int = 50,
    ) -> list[ResearchSession]:
        """
        Most recent `limit` turns in a conversation, oldest first (the
        order a prompt transcript -- and a thread replay view -- needs).
        Scoped to `owner_id` so a caller can never enumerate another
        user's turns even if they guess a `conversation_id`.
        """

        statement = (
            select(ResearchSession)
            .where(
                ResearchSession.conversation_id == conversation_id,
                ResearchSession.owner_id == owner_id,
            )
            .order_by(ResearchSession.created_at.desc())
            .limit(limit)
        )

        result = await self.session.execute(statement)

        return list(reversed(result.scalars().all()))
