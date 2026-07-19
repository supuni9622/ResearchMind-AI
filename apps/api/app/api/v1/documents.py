from __future__ import annotations

import structlog
from fastapi import (
    APIRouter,
    Depends,
    File,
    UploadFile,
    status,
)

# from app.ai.knowledge.processing.enums import DocumentFormat
# from app.ai.knowledge.processing.interfaces import ParseRequest
from app.ai.knowledge.upload.service import UploadService
from app.ai.knowledge.vectorstores.enums import VectorStoreProvider
from app.ai.knowledge.vectorstores.service import VectorStoreService
from app.auth.dependencies import get_current_user
from app.core.settings import settings
from app.dependencies import (
    # get_document_processing_service,
    get_document_repository,
    get_upload_service,
    get_vectorstore_service,
)
from app.exceptions.base import ValidationException
from app.models.user import User
from app.repositories.document import DocumentRepository
from app.schemas.document import (
    DocumentKnowledgeStats,
    DocumentResponse,
    DocumentUploadResponse,
)

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
    response_model=list[DocumentResponse],
    summary="List the current user's documents",
)
async def list_documents(
    current_user: User = Depends(get_current_user),
    repository: DocumentRepository = Depends(get_document_repository),
) -> list[DocumentResponse]:
    """
    List documents owned by the authenticated user.

    Newest first. Scoped to `current_user.id` — a user can never see
    another user's documents.
    """

    documents = await repository.list_by_owner(current_user.id)

    return [DocumentResponse.model_validate(document) for document in documents]


@router.get(
    "/stats",
    response_model=DocumentKnowledgeStats,
    summary="Read knowledge-base counts for the current user",
)
async def document_knowledge_stats(
    current_user: User = Depends(get_current_user),
    vectorstore_service: VectorStoreService = Depends(get_vectorstore_service),
) -> DocumentKnowledgeStats:
    """Return exact owner-scoped counts of indexed chunks and embeddings.

    Each indexed chunk is represented by one dense embedding/vector, so both
    values are intentionally equal until the index supports multiple vectors
    per chunk.
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
    current_user: User = Depends(get_current_user),
    upload_service: UploadService = Depends(get_upload_service),
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

    file.file.seek(0, 2)
    size_bytes = file.file.tell()
    file.file.seek(0)

    document = await upload_service.upload(
        owner_id=current_user.id,
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
