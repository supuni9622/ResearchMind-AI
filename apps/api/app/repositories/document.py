from __future__ import annotations

import uuid
from typing import Literal

from sqlalchemy import ColumnElement, and_, exists, func, not_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document

DocumentKind = Literal["pdf", "docx", "markdown", "other"]


def _kind_condition(kind: DocumentKind) -> ColumnElement[bool]:
    """
    Build the SQL condition for a document "kind" bucket.

    Mirrors the classification in apps/web's `getDocKind` (content-type
    first, filename extension as a fallback) so server-side filtering
    agrees with the client's existing kind labels.
    """

    is_pdf = or_(Document.content_type.ilike("%pdf%"), Document.filename.ilike("%.pdf"))
    is_docx = or_(
        Document.content_type.ilike("%word%"),
        Document.filename.ilike("%.docx"),
        Document.filename.ilike("%.doc"),
    )
    is_markdown = or_(Document.content_type.ilike("%markdown%"), Document.filename.ilike("%.md"))

    if kind == "pdf":
        return is_pdf
    if kind == "docx":
        return is_docx
    if kind == "markdown":
        return is_markdown
    return not_(or_(is_pdf, is_docx, is_markdown))


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

    # Duplicate detection
    async def find_by_owner_and_hash(
        self,
        *,
        owner_id: uuid.UUID,
        sha256: str,
    ) -> Document | None:
        """
        Retrieve a document owned by owner_id with the given checksum.

        Historical data may contain more than one document with the
        same (owner_id, checksum) pair, since this was not always
        enforced as unique. The most recently created match is
        returned rather than raising, so duplicate detection stays
        resilient to that pre-existing state.
        """

        statement = (
            select(Document)
            .where(
                Document.owner_id == owner_id,
                Document.checksum == sha256,
            )
            .order_by(Document.created_at.desc())
            .limit(1)
        )

        result = await self.session.execute(statement)

        return result.scalars().first()

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

    async def get_by_ids_for_owner(
        self,
        document_ids: list[uuid.UUID],
        *,
        owner_id: uuid.UUID,
    ) -> list[Document]:
        """
        Resolve a batch of document ids, scoped to `owner_id`.

        Silently drops ids that don't exist or belong to another owner --
        callers that need "all requested ids must resolve" (e.g. "@document"
        mentions) compare the returned list's length/ids against what was
        requested and raise their own not-found error.
        """

        if not document_ids:
            return []

        statement = select(Document).where(
            Document.owner_id == owner_id,
            Document.id.in_(document_ids),
        )

        result = await self.session.execute(statement)

        return list(result.scalars().all())

    # Paginated + filtered document listing (the /documents page)
    async def list_by_owner_page(
        self,
        owner_id: uuid.UUID,
        *,
        limit: int,
        offset: int,
        search: str | None = None,
        kind: DocumentKind | None = None,
        project_id: uuid.UUID | None = None,
    ) -> tuple[list[Document], int]:
        """
        Retrieve one page of documents owned by a user, newest first.

        `search` matches against the filename (case-insensitive substring).
        Returns the page alongside the total count matching the filters,
        so callers can render "page X of Y" without a second round trip.

        `project_id=None` means personal documents only (`project_id IS
        NULL`), not "every project" -- callers pass their current
        workspace context explicitly, same contract as
        `ConversationRepository.list_conversations_page`.
        """

        conditions: list[ColumnElement[bool]] = [
            Document.owner_id == owner_id,
            Document.project_id == project_id,
        ]

        if search:
            conditions.append(Document.filename.ilike(f"%{search}%"))

        if kind:
            conditions.append(_kind_condition(kind))

        filters = and_(*conditions)

        count_statement = select(func.count()).select_from(Document).where(filters)
        total = await self.session.scalar(count_statement) or 0

        statement = (
            select(Document)
            .where(filters)
            .order_by(Document.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(statement)

        return list(result.scalars().all()), total

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
