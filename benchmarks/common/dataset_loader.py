"""
Benchmark dataset loader.

Loads canonical benchmark datasets from the local filesystem.

Benchmark datasets are intentionally independent from production
infrastructure and are stored as version-controlled engineering assets.

Currently supported:

- ProcessedDocument datasets

Future benchmark datasets may include:

- Chunks
- Embeddings
- Retrieval results
- Ground truth annotations
"""

from __future__ import annotations

import json
from pathlib import Path

from app.ai.knowledge.processing.models import ProcessedDocument


class DatasetLoader:
    """
    Loads benchmark datasets.
    """

    def load_documents(
        self,
        dataset_path: Path,
    ) -> list[ProcessedDocument]:
        """
        Load every ProcessedDocument within a benchmark dataset.

        Expected directory structure:

            dataset_path/
                paper_001/
                    processed_document.json

                paper_002/
                    processed_document.json

                ...

        Args:
            dataset_path:
                Root benchmark dataset directory.

        Returns:
            Loaded processed documents ordered by directory name.
        """

        if not dataset_path.exists():
            raise FileNotFoundError(f"Dataset directory does not exist: {dataset_path}")

        documents: list[ProcessedDocument] = []

        for document_directory in sorted(path for path in dataset_path.iterdir() if path.is_dir()):
            processed_document_path = document_directory / "processed_document.json"

            if not processed_document_path.exists():
                raise FileNotFoundError(f"Missing benchmark artifact: {processed_document_path}")

            with processed_document_path.open(
                "r",
                encoding="utf-8",
            ) as file:
                payload = json.load(file)

            documents.append(ProcessedDocument.model_validate(payload))

        return documents
