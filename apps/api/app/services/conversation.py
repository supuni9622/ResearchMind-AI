from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

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

    async def list_for_owner(
        self,
        *,
        owner_id: uuid.UUID,
        limit: int = 50,
    ) -> list[Conversation]:
        """List conversation summaries for the authenticated owner."""

        return await self.repository.list_conversations_for_owner(
            owner_id=owner_id,
            limit=limit,
        )

    async def list_messages(
        self,
        *,
        conversation_id: uuid.UUID,
        limit: int = 50,
    ) -> list[Message]:
        """Return persisted messages for an already owner-scoped conversation."""

        return await self.repository.list_messages(
            conversation_id=conversation_id,
            limit=limit,
        )

    async def get_first_user_prompt(
        self,
        *,
        conversation_id: uuid.UUID,
    ) -> str | None:
        """Return the first question, used as the title-generation source."""

        message = await self.repository.get_first_user_message(
            conversation_id=conversation_id,
        )
        return message.content if message is not None else None

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

        turn_started_at = datetime.now(UTC)

        await self.repository.add_message(
            Message(
                conversation_id=conversation_id,
                role=MessageRole.USER,
                content=user_prompt,
                created_at=turn_started_at,
            ),
        )

        await self.repository.add_message(
            Message(
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content=assistant_content,
                provider=provider,
                model=model,
                created_at=turn_started_at + timedelta(microseconds=1),
            ),
        )

        # Messages are separate rows, so touching the parent explicitly is
        # necessary for the conversation sidebar's activity ordering.
        await self.repository.touch_conversation(
            conversation_id=conversation_id,
            updated_at=datetime.now(UTC),
        )

        await self.session.commit()

    async def set_title(
        self,
        *,
        conversation_id: uuid.UUID,
        title: str,
    ) -> None:
        """Persist the title generated from the conversation's first question."""

        await self.repository.set_title(
            conversation_id=conversation_id,
            title=title,
        )
        await self.session.commit()

    async def claim_title_generation(
        self,
        *,
        conversation_id: uuid.UUID,
    ) -> uuid.UUID | None:
        """Claim the one title-generation attempt permitted for a conversation."""

        token = await self.repository.claim_title_generation(
            conversation_id=conversation_id,
        )
        await self.session.commit()
        return token

    async def complete_title_generation(
        self,
        *,
        conversation_id: uuid.UUID,
        token: uuid.UUID,
        title: str,
    ) -> bool:
        """Store a title only when this caller still owns the generation lease."""

        stored = await self.repository.complete_title_generation(
            conversation_id=conversation_id,
            token=token,
            title=title,
        )
        await self.session.commit()
        return stored

    async def release_title_generation(
        self,
        *,
        conversation_id: uuid.UUID,
        token: uuid.UUID,
    ) -> None:
        """Release a failed title-generation lease so a later turn can retry."""

        await self.repository.release_title_generation(
            conversation_id=conversation_id,
            token=token,
        )
        await self.session.commit()
