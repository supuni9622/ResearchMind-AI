from __future__ import annotations

import uuid

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.base import NotFoundException
from app.models.conversation import Conversation, Message
from app.models.enums import MessageRole
from app.repositories.conversation import ConversationRepository


class ConversationService:
    """
    Service responsible for Conversation/Message business logic.

    Services coordinate repositories,
    enforce business rules,
    and manage database transactions.
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session
        self.repository = ConversationRepository(session)

    async def get_or_create(
        self,
        *,
        conversation_id: uuid.UUID | None,
        owner_id: uuid.UUID,
    ) -> Conversation:
        """
        Loads an existing conversation scoped to `owner_id`, or starts a
        new one when `conversation_id` is not given.
        """

        if conversation_id is not None:
            conversation = await self.repository.get_by_id_for_owner(
                conversation_id=conversation_id,
                owner_id=owner_id,
            )

            if conversation is None:
                raise NotFoundException(
                    message=f"Conversation '{conversation_id}' was not found.",
                )

            return conversation

        conversation = await self.repository.create(
            Conversation(owner_id=owner_id),
        )

        await self.session.commit()

        return conversation

    async def load_history(
        self,
        *,
        conversation_id: uuid.UUID,
        limit: int = 50,
    ) -> list[BaseMessage]:
        """
        Prior turns as langchain messages, oldest first.
        """

        messages = await self.repository.list_messages(
            conversation_id=conversation_id,
            limit=limit,
        )

        return [
            HumanMessage(content=message.content)
            if message.role == MessageRole.USER
            else AIMessage(content=message.content)
            for message in messages
        ]

    async def append_turn(
        self,
        *,
        conversation_id: uuid.UUID,
        user_prompt: str,
        assistant_content: str,
        provider: str | None = None,
        model: str | None = None,
    ) -> None:
        """
        Persists both halves of a completed exchange.
        """

        await self.repository.add_message(
            Message(
                conversation_id=conversation_id,
                role=MessageRole.USER,
                content=user_prompt,
            ),
        )

        await self.repository.add_message(
            Message(
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content=assistant_content,
                provider=provider,
                model=model,
            ),
        )

        await self.session.commit()
