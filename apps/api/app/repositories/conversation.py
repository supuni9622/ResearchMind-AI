from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message


class ConversationRepository:
    """
    Repository responsible for Conversation/Message persistence.

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
        conversation: Conversation,
    ) -> Conversation:
        """
        Persist a new conversation.

        The transaction is not committed here.
        """

        self.session.add(conversation)

        await self.session.flush()
        await self.session.refresh(conversation)

        return conversation

    async def get_by_id_for_owner(
        self,
        *,
        conversation_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> Conversation | None:
        """
        Retrieve a conversation by primary key, scoped to its owner so a
        caller can never load another user's conversation by id.
        """

        statement = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.owner_id == owner_id,
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def add_message(
        self,
        message: Message,
    ) -> Message:
        """
        Persist a new message.

        The transaction is not committed here.
        """

        self.session.add(message)

        await self.session.flush()
        await self.session.refresh(message)

        return message

    async def list_messages(
        self,
        *,
        conversation_id: uuid.UUID,
        limit: int = 50,
    ) -> list[Message]:
        """
        Most recent `limit` messages in a conversation, oldest first (the
        order a prompt transcript needs).
        """

        statement = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )

        result = await self.session.execute(statement)

        return list(reversed(result.scalars().all()))
