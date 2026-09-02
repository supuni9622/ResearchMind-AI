# Upload constants - Upload limits, supported MIME types
"""
Upload platform constants.
"""

from pathlib import Path

# ---------------------------------------------------------------------
# File Size
# ---------------------------------------------------------------------

MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

# ---------------------------------------------------------------------
# Supported MIME Types
# ---------------------------------------------------------------------

SUPPORTED_CONTENT_TYPES = frozenset(
    {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/markdown",
        "text/plain",
        # Image-to-RAG ingestion (Wave 4, docs/PRIORITIZED_ROADMAP.md) --
        # OCR'd via Docling's default image pipeline, see
        # `processing/parsers/docling.py` and `processing/enums.py`.
        "image/png",
        "image/jpeg",
        "image/webp",
        "image/gif",
    }
)

# ---------------------------------------------------------------------
# Supported File Extensions
# ---------------------------------------------------------------------

SUPPORTED_EXTENSIONS = frozenset(
    {
        ".pdf",
        ".docx",
        ".md",
        ".txt",
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".gif",
    }
)


def get_extension(filename: str) -> str:
    """Return a lowercase file extension."""

    return Path(filename).suffix.lower()
