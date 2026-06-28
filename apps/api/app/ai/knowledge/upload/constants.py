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
    }
)


def get_extension(filename: str) -> str:
    """Return a lowercase file extension."""

    return Path(filename).suffix.lower()
