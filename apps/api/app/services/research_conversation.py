from __future__ import annotations

import uuid
from uuid import uuid4

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.base import NotFoundException
from app.models.research import ResearchConversation
from app.repositories.research import ResearchRepository


class ResearchConversationService:
    """
    Service responsible for ResearchConversation business logic --
    mirrors `ConversationService` (Chat's equivalent), grouping
    `ResearchSession` turns into a continuing thread instead of each
    `/research` call being an island.
    """

    def __init__(
        self,
        session: AsyncSession,
        repository: ResearchRepository | None = None,
    ) -> None:
        self.session = session
        self.repository = repository or ResearchRepository(session)

    async def get_or_create(
        self,
        *,
        conversation_id: uuid.UUID | None,
        owner_id: uuid.UUID,
    ) -> ResearchConversation:
        """
        Loads an existing conversation scoped to `owner_id`, or starts a
        new one when `conversation_id` is not given.
        """

        if conversation_id is not None:
            conversation = await self.repository.get_conversation_by_id_for_owner(
                conversation_id=conversation_id,
                owner_id=owner_id,
            )

            if conversation is None:
                raise NotFoundException(
                    message=f"Research conversation '{conversation_id}' was not found.",
                )

            return conversation

        # `id` is generated here rather than left to the ORM column
        # default: it needs to be known immediately (used as the
        # session-memory boundary and stamped onto the turn's
        # `ResearchSession` row before that row is flushed), not only
        # after a real flush executes the mapped-column default.
        conversation = await self.repository.create_conversation(
            ResearchConversation(id=uuid4(), owner_id=owner_id),
        )

        await self.session.commit()

        return conversation

    async def set_title_from_first_query(
        self,
        *,
        conversation: ResearchConversation,
        query: str,
    ) -> None:
        """
        Best-effort auto-title, set once from the conversation's first
        query and never overwritten after (mirrors `use-chat.ts`'s
        client-side `titleFrom()`, done server-side here since Research
        conversations are listed via `GET /research/conversations`
        rather than kept in localStorage). A no-op once `title` is
        already set -- `conversation.title` starts `None` only for a
        conversation that was just created by `get_or_create()`.
        """

        if conversation.title is not None:
            return

        title = query.strip()[:255]

        if not title:
            return

        conversation.title = title

        await self.session.commit()

    async def load_history(
        self,
        *,
        conversation_id: uuid.UUID,
        owner_id: uuid.UUID,
        limit: int = 50,
    ) -> list[BaseMessage]:
        """
        Prior turns as langchain messages, oldest first -- folded into the
        next turn's prompt the same way `chat.py::_format_transcript`
        folds `ConversationService.load_history()`.
        """

        sessions = await self.repository.list_sessions_for_conversation(
            conversation_id=conversation_id,
            owner_id=owner_id,
            limit=limit,
        )

        messages: list[BaseMessage] = []

        for research_session in sessions:
            messages.append(HumanMessage(content=research_session.query))
            messages.append(AIMessage(content=research_session.answer))

        return messages
