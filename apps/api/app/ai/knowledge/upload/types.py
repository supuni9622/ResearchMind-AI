# Shared upload types - Shared typing aliases
from pathlib import Path
from typing import NewType

DocumentId = NewType("DocumentId", str)
Checksum = NewType("Checksum", str)
MimeType = NewType("MimeType", str)
FileSize = NewType("FileSize", int)
FilePath = NewType("FilePath", Path)
