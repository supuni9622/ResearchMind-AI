from __future__ import annotations

import uuid

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document


class DocumentRepository:
    """
    Repository responsible for Document persistence.

    This class contains only database operations.

    It must never:
        - contain business logic
        - call external services
        - upload files
        - commit or rollback transactions
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # Upload workflow
    async def create(
        self,
        document: Document,
    ) -> Document:
        """
        Persist a new document.

        The transaction is not committed here.
        """

        self.session.add(document)

        await self.session.flush()
        await self.session.refresh(document)

        return document

    # API, processing
    async def get_by_id(
        self,
        document_id: uuid.UUID,
    ) -> Document | None:
        """
        Retrieve a document by its primary key.
        """

        statement = select(Document).where(
            Document.id == document_id,
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    # Duplicate detection
    async def get_by_checksum(
        self,
        checksum: str,
    ) -> Document | None:
        """
        Retrieve a document by checksum.
        """

        statement = select(Document).where(
            Document.checksum == checksum,
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    # S3 operations
    async def get_by_storage_key(
        self,
        storage_key: str,
    ) -> Document | None:
        """
        Retrieve a document by storage key.
        """

        statement = select(Document).where(
            Document.storage_key == storage_key,
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    # User document listing
    async def list_by_owner(
        self,
        owner_id: uuid.UUID,
    ) -> list[Document]:
        """
        Retrieve all documents owned by a user.
        """

        statement = (
            select(Document)
            .where(Document.owner_id == owner_id)
            .order_by(Document.created_at.desc())
        )

        result = await self.session.execute(statement)

        return list(result.scalars().all())

    # Fast duplicate check
    async def exists_by_checksum(
        self,
        checksum: str,
    ) -> bool:
        """
        Check whether a document already exists
        with the given checksum.
        """

        statement = select(
            exists().where(
                Document.checksum == checksum,
            )
        )

        result = await self.session.scalar(statement)

        return bool(result)

    # Processing state transitions
    async def update(
        self,
        document: Document,
    ) -> Document:
        """
        Flush pending document changes.

        The transaction is not committed here.
        """

        await self.session.flush()
        await self.session.refresh(document)

        return document

    # Document deletion
    async def delete(
        self,
        document: Document,
    ) -> None:
        """
        Delete a document.

        The transaction is not committed here.
        """

        await self.session.delete(document)

        await self.session.flush()
