"""
Language metadata provider.

Detects the primary language of a document.

Language detection is performed on the extracted document text rather
than the original file.
"""

from __future__ import annotations

from langdetect import DetectorFactory, LangDetectException, detect_langs

from app.ai.knowledge.processing.metadata.base import BaseMetadataProvider
from app.ai.knowledge.processing.metadata.models import (
    LanguageMetadata,
    MetadataUpdate,
)
from app.ai.knowledge.processing.models import ProcessedDocument

# Make language detection deterministic.
DetectorFactory.seed = 0


class LanguageMetadataProvider(BaseMetadataProvider):
    """
    Detects the primary language of a processed document.
    """

    @property
    def provider_name(self) -> str:
        return "Language Detection"

    async def enrich(
        self,
        *,
        document: ProcessedDocument,
        file_path,
    ) -> MetadataUpdate:
        """
        Detect the primary language of the document.
        """

        text = document.raw_text.strip()

        if not text:
            return MetadataUpdate()

        try:
            languages = detect_langs(text)

        except LangDetectException:
            return MetadataUpdate()

        if not languages:
            return MetadataUpdate()

        primary = languages[0]

        return MetadataUpdate(
            language=LanguageMetadata(
                language=primary.lang,
                confidence=primary.prob,
            )
        )
