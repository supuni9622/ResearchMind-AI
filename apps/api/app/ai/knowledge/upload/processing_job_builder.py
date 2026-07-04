"""
Builder for document processing queue jobs.

Transforms a persisted Document into the canonical ProcessingJob
enqueued for asynchronous processing.
"""

from __future__ import annotations

from app.infrastructure.queue.models import ProcessingJob
from app.models.document import Document


class ProcessingJobBuilder:
    """
    Builds processing queue jobs from persisted documents.
    """

    @staticmethod
    def build(
        document: Document,
    ) -> ProcessingJob:
        """
        Build the canonical processing job.
        """

        return ProcessingJob(
            document_id=document.id,
            owner_id=document.owner_id,
            storage_key=document.storage_key,
        )
