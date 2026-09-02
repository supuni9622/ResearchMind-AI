"""
Chat attachment constants -- size/count limits, supported image types.
"""

from pathlib import Path

# ---------------------------------------------------------------------
# Limits (docs/PRIORITIZED_ROADMAP.md Wave 4: "chat-only image
# attachments (<=5/turn)")
# ---------------------------------------------------------------------

MAX_ATTACHMENT_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

MAX_ATTACHMENTS_PER_TURN = 5

# ---------------------------------------------------------------------
# Supported MIME Types
# ---------------------------------------------------------------------

SUPPORTED_IMAGE_CONTENT_TYPES = frozenset(
    {
        "image/png",
        "image/jpeg",
        "image/webp",
        "image/gif",
    }
)

# ---------------------------------------------------------------------
# Supported File Extensions
# ---------------------------------------------------------------------

SUPPORTED_IMAGE_EXTENSIONS = frozenset(
    {
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
