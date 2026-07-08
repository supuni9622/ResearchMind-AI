"""
Pipeline benchmark dataset loading.

Reuses the shared ``DatasetLoader`` (also used by the Chunking and
Embedding benchmarks) for parsing and validating benchmark documents,
and pairs each document with the on-disk size of its source
``processed_document.json``. Artifact-size measurement is specific to
the Pipeline Benchmark, so it is not added to the shared loader.
"""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

from app.ai.knowledge.processing.models import ProcessedDocument

from benchmarks.common.dataset_loader import DatasetLoader


class PipelineDatasetEntry(NamedTuple):
    document: ProcessedDocument
    source_size_bytes: int


def load_pipeline_dataset(
    dataset_path: Path,
) -> list[PipelineDatasetEntry]:
    """
    Load every benchmark document together with its source artifact size.

    Args:
        dataset_path:
            Root benchmark dataset directory (e.g.
            ``benchmarks/datasets/research-papers``).

    Returns:
        Entries ordered by directory name, matching DatasetLoader's order.
    """

    documents = DatasetLoader().load_documents(dataset_path)

    document_directories = sorted(path for path in dataset_path.iterdir() if path.is_dir())

    if len(document_directories) != len(documents):
        raise RuntimeError("Dataset directory listing changed while loading the benchmark dataset.")

    entries: list[PipelineDatasetEntry] = []

    for directory, document in zip(document_directories, documents, strict=True):
        size_bytes = (directory / "processed_document.json").stat().st_size
        entries.append(
            PipelineDatasetEntry(
                document=document,
                source_size_bytes=size_bytes,
            )
        )

    return entries
