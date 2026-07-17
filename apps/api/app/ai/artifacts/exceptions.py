"""
Artifact Platform exceptions.
"""


class ArtifactError(Exception):
    """Base exception for the Artifact Platform."""


class ArtifactWriteError(ArtifactError):
    """Raised when persisting an artifact fails."""


class ArtifactReadError(ArtifactError):
    """Raised when reading a persisted artifact fails for a reason other than it not existing."""


class ArtifactNotFoundError(ArtifactError):
    """Raised when a required artifact file does not exist in storage."""
