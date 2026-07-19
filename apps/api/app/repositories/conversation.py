from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, case, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message
from app.models.enums import MessageRole


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
            # PostgreSQL's `now()` is transaction-scoped, so both rows of
            # a turn can share the exact timestamp. Query newest-first for
            # the limit, with assistant first on ties; reversing below then
            # returns the natural User → Assistant conversation flow.
            .order_by(
                Message.created_at.desc(),
                case((Message.role == MessageRole.USER, 0), else_=1).desc(),
            )
            .limit(limit)
        )

        result = await self.session.execute(statement)

        return list(reversed(result.scalars().all()))

    async def list_messages_page(
        self,
        *,
        conversation_id: uuid.UUID,
        before_message_id: uuid.UUID | None,
        limit: int,
    ) -> tuple[list[Message], uuid.UUID | None]:
        """Return one newest-first cursor page, presented oldest first."""

        statement = select(Message).where(Message.conversation_id == conversation_id)
        if before_message_id is not None:
            cursor = await self.session.scalar(
                select(Message).where(
                    Message.id == before_message_id,
                    Message.conversation_id == conversation_id,
                )
            )
            if cursor is None:
                return [], None
            statement = statement.where(
                or_(
                    Message.created_at < cursor.created_at,
                    and_(
                        Message.created_at == cursor.created_at,
                        Message.id < cursor.id,
                    ),
                )
            )

        rows = list(
            (
                await self.session.execute(
                    statement.order_by(Message.created_at.desc(), Message.id.desc()).limit(
                        limit + 1
                    )
                )
            ).scalars()
        )
        has_more = len(rows) > limit
        page = rows[:limit]
        return list(reversed(page)), (page[-1].id if has_more and page else None)

    async def list_messages_after(
        self,
        *,
        conversation_id: uuid.UUID,
        after: datetime | None,
    ) -> list[Message]:
        """Load uncompacted messages oldest first; used only for compaction."""

        statement = select(Message).where(Message.conversation_id == conversation_id)
        if after is not None:
            statement = statement.where(Message.created_at > after)
        result = await self.session.execute(
            statement.order_by(Message.created_at.asc(), Message.id.asc())
        )
        return list(result.scalars().all())

    async def get_first_user_message(
        self,
        *,
        conversation_id: uuid.UUID,
    ) -> Message | None:
        """Return the question that started a conversation."""

        statement = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.role == MessageRole.USER,
            )
            .order_by(Message.created_at.asc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_conversations_for_owner(
        self,
        *,
        owner_id: uuid.UUID,
        limit: int = 50,
    ) -> list[Conversation]:
        """Return a user's conversations, newest activity first."""

        statement = (
            select(Conversation)
            .where(Conversation.owner_id == owner_id)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
        )

        result = await self.session.execute(statement)

        return list(result.scalars().all())

    async def list_conversations_page(
        self,
        *,
        owner_id: uuid.UUID,
        before_conversation_id: uuid.UUID | None,
        limit: int,
    ) -> tuple[list[Conversation], uuid.UUID | None]:
        """Return owner-scoped conversations with a stable activity cursor."""

        statement = select(Conversation).where(Conversation.owner_id == owner_id)
        if before_conversation_id is not None:
            cursor = await self.session.scalar(
                select(Conversation).where(
                    Conversation.id == before_conversation_id,
                    Conversation.owner_id == owner_id,
                )
            )
            if cursor is None:
                return [], None
            statement = statement.where(
                or_(
                    Conversation.updated_at < cursor.updated_at,
                    and_(
                        Conversation.updated_at == cursor.updated_at,
                        Conversation.id < cursor.id,
                    ),
                )
            )

        rows = list(
            (
                await self.session.execute(
                    statement.order_by(
                        Conversation.updated_at.desc(), Conversation.id.desc()
                    ).limit(limit + 1)
                )
            ).scalars()
        )
        has_more = len(rows) > limit
        page = rows[:limit]
        return page, (page[-1].id if has_more and page else None)

    async def set_history_compaction(
        self,
        *,
        conversation_id: uuid.UUID,
        summary: str,
        through_at: datetime,
    ) -> None:
        """Persist prompt-only compaction state without deleting messages."""

        await self.session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(
                history_summary=summary,
                history_compacted_through_at=through_at,
            )
        )

    async def touch_conversation(
        self,
        *,
        conversation_id: uuid.UUID,
        updated_at: datetime,
        title: str | None = None,
    ) -> None:
        """Record activity on a conversation after one of its turns is saved."""

        values: dict[str, object] = {"updated_at": updated_at}
        if title is not None:
            values["title"] = title

        await self.session.execute(
            update(Conversation).where(Conversation.id == conversation_id).values(**values)
        )

    async def set_title(
        self,
        *,
        conversation_id: uuid.UUID,
        title: str,
    ) -> None:
        """Store the generated title derived from the conversation's first question."""

        await self.session.execute(
            update(Conversation).where(Conversation.id == conversation_id).values(title=title)
        )

    async def claim_title_generation(
        self,
        *,
        conversation_id: uuid.UUID,
        lease_timeout: timedelta = timedelta(minutes=5),
    ) -> uuid.UUID | None:
        """Atomically lease title generation for an untitled conversation."""

        token = uuid.uuid4()
        now = datetime.now(UTC)
        stale_before = now - lease_timeout
        result = await self.session.execute(
            update(Conversation)
            .where(
                Conversation.id == conversation_id,
                Conversation.title.is_(None),
                (
                    Conversation.title_generation_started_at.is_(None)
                    | (Conversation.title_generation_started_at < stale_before)
                ),
            )
            .values(
                title_generation_token=token,
                title_generation_started_at=now,
            )
            .returning(Conversation.id)
        )
        return token if result.scalar_one_or_none() is not None else None

    async def complete_title_generation(
        self,
        *,
        conversation_id: uuid.UUID,
        token: uuid.UUID,
        title: str,
    ) -> bool:
        """Set a claimed title only if this worker still owns the lease."""

        result = await self.session.execute(
            update(Conversation)
            .where(
                Conversation.id == conversation_id,
                Conversation.title.is_(None),
                Conversation.title_generation_token == token,
            )
            .values(
                title=title,
                title_generation_token=None,
                title_generation_started_at=None,
            )
            .returning(Conversation.id)
        )
        return result.scalar_one_or_none() is not None

    async def release_title_generation(
        self,
        *,
        conversation_id: uuid.UUID,
        token: uuid.UUID,
    ) -> None:
        """Release a failed title-generation lease without touching a newer one."""

        await self.session.execute(
            update(Conversation)
            .where(
                Conversation.id == conversation_id,
                Conversation.title_generation_token == token,
            )
            .values(
                title_generation_token=None,
                title_generation_started_at=None,
            )
        )
