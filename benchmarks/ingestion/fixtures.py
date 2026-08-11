"""
Ingestion fidelity fixture loading.

A fixture pairs a benchmark document (`paper-NNN/processed_document.json`,
loaded the same way `DatasetLoader` loads any other benchmark document)
with hand-verified minimum heading/table counts recorded in
`ingestion_fidelity_fixtures.json` -- see that file's own `notes` field
for how those minimums were established.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.ai.knowledge.processing.models import ProcessedDocument
from pydantic import BaseModel, ConfigDict

FIXTURE_MANIFEST_FILENAME = "ingestion_fidelity_fixtures.json"


class IngestionFidelityFixture(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_dir: str
    filename: str
    expected_min_headings: int
    expected_min_tables: int


class IngestionFidelityFixtureManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str
    notes: str = ""
    fixtures: list[IngestionFidelityFixture]


def load_fixture_manifest(
    dataset_path: Path,
) -> IngestionFidelityFixtureManifest:
    """
    Load the fixture manifest from a benchmark dataset directory.

    Raises:
        FileNotFoundError:
            If the manifest file does not exist.
    """

    manifest_path = dataset_path / FIXTURE_MANIFEST_FILENAME

    if not manifest_path.exists():
        raise FileNotFoundError(f"Ingestion fidelity fixture manifest not found: {manifest_path}")

    with manifest_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    return IngestionFidelityFixtureManifest.model_validate(payload)


def load_fixture_document(
    dataset_path: Path,
    fixture: IngestionFidelityFixture,
) -> ProcessedDocument | None:
    """
    Load a single fixture's cached `ProcessedDocument`.

    Returns `None` (rather than raising) when the artifact is missing or
    fails schema validation -- both are exactly the "document fails
    ingestion outright" case `parse_success_rate` needs to count, not an
    error in the benchmark itself.
    """

    processed_document_path = dataset_path / fixture.document_dir / "processed_document.json"

    if not processed_document_path.exists():
        return None

    try:
        with processed_document_path.open("r", encoding="utf-8") as file:
            payload = json.load(file)

        return ProcessedDocument.model_validate(payload)
    except (json.JSONDecodeError, ValueError):
        return None
