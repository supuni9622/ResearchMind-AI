from __future__ import annotations

from uuid import UUID

import structlog
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

# from app.ai.knowledge.processing.enums import DocumentFormat
# from app.ai.knowledge.processing.interfaces import ParseRequest
from app.ai.knowledge.upload.service import UploadService
from app.ai.knowledge.vectorstores.enums import VectorStoreProvider
from app.ai.knowledge.vectorstores.service import VectorStoreService
from app.auth.dependencies import get_current_user
from app.core.settings import settings
from app.db.session import get_db
from app.dependencies import (
    # get_document_processing_service,
    get_document_repository,
    get_upload_service,
    get_vectorstore_service,
)
from app.dependencies.project import get_project_authorization_service
from app.dependencies.upload import get_document_storage
from app.exceptions.base import NotFoundException, ValidationException
from app.infrastructure.storage.interfaces import DocumentStorage
from app.models.user import User
from app.repositories.document import DocumentKind, DocumentRepository
from app.schemas.document import (
    DocumentKnowledgeStats,
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from app.services.project_authorization import ProjectAuthorizationService

# from app.services.document_processing_service import (
#     DocumentProcessingService,
# )

logger = structlog.get_logger()

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List the current user's documents",
)
async def list_documents(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, min_length=1, max_length=200),
    kind: DocumentKind | None = Query(default=None),
    # Omitted -> personal documents only (`project_id IS NULL`), not
    # "every project" -- same contract as `GET /chat/conversations`.
    project_id: UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    repository: DocumentRepository = Depends(get_document_repository),
) -> DocumentListResponse:
    """
    List documents owned by the authenticated user, paginated.

    Newest first. Scoped to `current_user.id` — a user can never see
    another user's documents. `search` matches the filename
    (case-insensitive substring); `kind` filters by document type.
    """

    documents, total = await repository.list_by_owner_page(
        current_user.id,
        limit=limit,
        offset=offset,
        search=search,
        kind=kind,
        project_id=project_id,
    )

    return DocumentListResponse(
        items=[DocumentResponse.model_validate(document) for document in documents],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/stats",
    response_model=DocumentKnowledgeStats,
    summary="Read knowledge-base counts for the current user",
)
async def document_knowledge_stats(
    project_id: UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    vectorstore_service: VectorStoreService = Depends(get_vectorstore_service),
) -> DocumentKnowledgeStats:
    """Return exact owner-scoped counts of indexed chunks and embeddings.

    Each indexed chunk is represented by one dense embedding/vector, so both
    values are intentionally equal until the index supports multiple vectors
    per chunk. `project_id` follows the same omit=personal-only contract as
    `GET /documents`.
    """

    if not await vectorstore_service.collection_exists(
        provider=VectorStoreProvider.QDRANT,
        collection_name=settings.qdrant_collection_name,
    ):
        embedding_count = 0
    else:
        embedding_count = await vectorstore_service.count(
            provider=VectorStoreProvider.QDRANT,
            collection_name=settings.qdrant_collection_name,
            owner_id=str(current_user.id),
            project_id=str(project_id) if project_id else None,
        )

    return DocumentKnowledgeStats(
        indexed_chunk_count=embedding_count,
        embedding_count=embedding_count,
    )


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document",
)
async def upload_document(
    file: UploadFile = File(...),
    project_id: UUID | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    upload_service: UploadService = Depends(get_upload_service),
    project_authorization: ProjectAuthorizationService = Depends(get_project_authorization_service),
    # processing_service: DocumentProcessingService = Depends(
    #     get_document_processing_service,
    # ),
) -> DocumentUploadResponse:
    """
    Upload a document to ResearchMind.

    Synchrounous Workflow (previous):

    1. Validate upload
    2. Upload original document to S3
    3. Persist document metadata
    4. Trigger synchronous document processing
    5. Return uploaded document metadata

    Processing failures do not fail the upload request.
    The document processing status records the outcome.

    Asynchrounous Workflow (current):

    1. Validate upload
    2. Upload original document to storage
    3. Persist document metadata
    4. Enqueue an asynchronous processing job
    5. Return immediately

    Document processing occurs asynchronously in the
    background worker.
    """

    if not file.filename:
        raise ValidationException(
            message="Uploaded file must have a filename.",
        )

    if project_id is not None:
        await project_authorization.authorize_project_access(
            user_id=current_user.id,
            project_id=project_id,
        )

    file.file.seek(0, 2)
    size_bytes = file.file.tell()
    file.file.seek(0)

    document = await upload_service.upload(
        owner_id=current_user.id,
        project_id=project_id,
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=size_bytes,
        file=file.file,
    )

    # This is the synchronous file processing flow - initial implementation
    # Commented this after created worker to process docs asynchrnously

    # parse_request = ParseRequest(
    #     document_id=document.id,
    #     storage_key=document.storage_key,
    #     filename=document.filename,
    #     content_type=document.content_type,
    #     document_format=DocumentFormat.from_content_type(
    #         document.content_type,
    #     ),
    # )

    # try:
    #     await processing_service.process(
    #         document=document,
    #         request=parse_request,
    #     )
    # except Exception:
    #     logger.exception(
    #         "document.processing_failed_after_upload",
    #         document_id=str(document.id),
    #         owner_id=str(current_user.id),
    #     )

    return DocumentUploadResponse.model_validate(document)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Permanently delete a document and its indexed content",
)
async def delete_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    repository: DocumentRepository = Depends(get_document_repository),
    vectorstore_service: VectorStoreService = Depends(get_vectorstore_service),
    storage: DocumentStorage = Depends(get_document_storage),
    session: AsyncSession = Depends(get_db),
) -> None:
    """
    Deletes the Qdrant vectors and S3 artifacts first, then the Postgres
    row -- both external deletes are idempotent, so if either raises, the
    row is left untouched and the caller can safely retry, rather than
    leaving a "deleted" document whose vectors or files silently leaked.
    """

    document = await repository.get_by_id(document_id)
    if document is None or document.owner_id != current_user.id:
        raise NotFoundException(message=f"Document '{document_id}' was not found.")

    # Mirrors `document_knowledge_stats`'s guard -- a document that was
    # never successfully indexed (e.g. upload failed before any vectors
    # were written) has nothing to delete, and the collection may not
    # exist yet in an otherwise-empty environment.
    if await vectorstore_service.collection_exists(
        provider=VectorStoreProvider.QDRANT,
        collection_name=settings.qdrant_collection_name,
    ):
        await vectorstore_service.delete_document(
            provider=VectorStoreProvider.QDRANT,
            collection_name=settings.qdrant_collection_name,
            document_id=str(document.id),
        )

    prefix = f"documents/{document.owner_id}/{document.id}"
    for key in await storage.list_keys(prefix=prefix):
        await storage.delete(key=key)

    await repository.delete(document)
    await session.commit()
