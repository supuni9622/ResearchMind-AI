# Contains values that never change between environments.

from pathlib import Path

# ==============================================================================
# Application Metadata
# ==============================================================================

APP_NAME = "ResearchMind AI"

APP_DESCRIPTION = "Production-grade AI Research & Intelligence Platform"

APP_VERSION = "0.1.0"

# ==============================================================================
# API
# ==============================================================================

API_V1_PREFIX = "/api/v1"

# ==============================================================================
# Pagination
# ==============================================================================

DEFAULT_PAGE_SIZE = 20

MAX_PAGE_SIZE = 100

# ==============================================================================
# Uploads
# ==============================================================================

MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100 MB

SUPPORTED_DOCUMENT_TYPES = {
    ".pdf",
    ".docx",
    ".txt",
    ".md",
}

# ==============================================================================
# Paths
# ==============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

DATASETS_DIRECTORY = PROJECT_ROOT / "datasets"

UPLOADS_DIRECTORY = PROJECT_ROOT / "uploads"

LOGS_DIRECTORY = PROJECT_ROOT / "logs"

TEMP_DIRECTORY = PROJECT_ROOT / "tmp"
