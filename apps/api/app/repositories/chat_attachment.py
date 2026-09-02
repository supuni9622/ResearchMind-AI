from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_attachment import ChatAttachment


class ChatAttachmentRepository:
    """
    Repository responsible for ChatAttachment persistence.

    This class contains only database operations. It must never contain
    business logic, call external services, or commit/rollback
    transactions -- mirrors `DocumentRepository`.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        attachment: ChatAttachment,
    ) -> ChatAttachment:
        """
        Persist a new attachment.

        The transaction is not committed here.
        """

        self.session.add(attachment)

        await self.session.flush()
        await self.session.refresh(attachment)

        return attachment

    async def get_by_ids_for_owner(
        self,
        attachment_ids: list[uuid.UUID],
        *,
        owner_id: uuid.UUID,
    ) -> list[ChatAttachment]:
        """
        Resolve a batch of attachment ids, scoped to `owner_id`.

        Silently drops ids that don't exist or belong to another owner --
        callers that need "all requested ids must resolve" compare the
        returned list's length/ids against what was requested and raise
        their own not-found error. Mirrors
        `DocumentRepository.get_by_ids_for_owner`.
        """

        if not attachment_ids:
            return []

        statement = select(ChatAttachment).where(
            ChatAttachment.owner_id == owner_id,
            ChatAttachment.id.in_(attachment_ids),
        )

        result = await self.session.execute(statement)

        return list(result.scalars().all())

    async def list_by_message_ids(
        self,
        message_ids: list[uuid.UUID],
    ) -> list[ChatAttachment]:
        """
        Batch-fetch attachments linked to any of the given messages, so
        rendering a page of conversation history costs one query rather
        than one per message.
        """

        if not message_ids:
            return []

        statement = select(ChatAttachment).where(
            ChatAttachment.message_id.in_(message_ids),
        )

        result = await self.session.execute(statement)

        return list(result.scalars().all())

    async def link_to_message(
        self,
        attachment_ids: list[uuid.UUID],
        *,
        conversation_id: uuid.UUID,
        message_id: uuid.UUID,
    ) -> None:
        """
        Attach a batch of previously-uploaded, still-unlinked attachments
        to the message/conversation their turn was just persisted under.

        The transaction is not committed here.
        """

        if not attachment_ids:
            return

        statement = select(ChatAttachment).where(
            ChatAttachment.id.in_(attachment_ids),
        )

        result = await self.session.execute(statement)

        for attachment in result.scalars().all():
            attachment.conversation_id = conversation_id
            attachment.message_id = message_id

        await self.session.flush()
