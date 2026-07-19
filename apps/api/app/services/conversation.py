from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.base import NotFoundException
from app.models.conversation import Conversation, Message
from app.models.enums import MessageRole
from app.repositories.conversation import ConversationRepository
from app.services.conversation_compaction import compact_conversation_history


@dataclass(frozen=True)
class ConversationPage:
    conversations: list[Conversation]
    next_cursor: uuid.UUID | None


@dataclass(frozen=True)
class MessagePage:
    messages: list[Message]
    next_cursor: uuid.UUID | None


@dataclass(frozen=True)
class PromptHistory:
    summary: str | None
    messages: list[BaseMessage]


@dataclass(frozen=True)
class PersistedConversationTurn:
    """Canonical identifiers for an exchange that was committed to history."""

    user_message_id: uuid.UUID
    assistant_message_id: uuid.UUID


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

    async def list_page_for_owner(
        self,
        *,
        owner_id: uuid.UUID,
        before_conversation_id: uuid.UUID | None,
        limit: int,
    ) -> ConversationPage:
        conversations, next_cursor = await self.repository.list_conversations_page(
            owner_id=owner_id,
            before_conversation_id=before_conversation_id,
            limit=limit,
        )
        return ConversationPage(conversations=conversations, next_cursor=next_cursor)

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

    async def list_messages_page(
        self,
        *,
        conversation_id: uuid.UUID,
        before_message_id: uuid.UUID | None,
        limit: int,
    ) -> MessagePage:
        messages, next_cursor = await self.repository.list_messages_page(
            conversation_id=conversation_id,
            before_message_id=before_message_id,
            limit=limit,
        )
        return MessagePage(messages=messages, next_cursor=next_cursor)

    async def compact_history_if_needed(
        self,
        *,
        conversation: Conversation,
        recent_message_limit: int,
        summary_max_characters: int,
    ) -> None:
        """Compact older prompt history while retaining every canonical row."""

        uncompacted = await self.repository.list_messages_after(
            conversation_id=conversation.id,
            after=conversation.history_compacted_through_at,
        )
        compactable = uncompacted[:-recent_message_limit]
        if not compactable:
            return

        summary = compact_conversation_history(
            existing_summary=conversation.history_summary,
            messages=compactable,
            max_characters=summary_max_characters,
        )
        await self.repository.set_history_compaction(
            conversation_id=conversation.id,
            summary=summary,
            through_at=compactable[-1].created_at,
        )
        await self.session.commit()
        conversation.history_summary = summary
        conversation.history_compacted_through_at = compactable[-1].created_at

    async def load_prompt_history(
        self,
        *,
        conversation: Conversation,
        recent_message_limit: int,
    ) -> PromptHistory:
        """Return compacted older context plus recent messages for a prompt."""

        messages = await self.repository.list_messages(
            conversation_id=conversation.id,
            limit=recent_message_limit,
        )
        return PromptHistory(
            summary=conversation.history_summary,
            messages=[
                HumanMessage(content=message.content)
                if message.role == MessageRole.USER
                else AIMessage(content=message.content)
                for message in messages
            ],
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
    ) -> PersistedConversationTurn:
        """
        Persists both halves of a completed exchange.
        """

        turn_started_at = datetime.now(UTC)

        user_message = await self.repository.add_message(
            Message(
                conversation_id=conversation_id,
                role=MessageRole.USER,
                content=user_prompt,
                created_at=turn_started_at,
            ),
        )

        assistant_message = await self.repository.add_message(
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

        return PersistedConversationTurn(
            user_message_id=user_message.id,
            assistant_message_id=assistant_message.id,
        )

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
