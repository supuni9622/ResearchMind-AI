"""
Query set for the `schema_validity_rate` benchmark (`EVALUATION_PLAN.md`
§13's fourth absolute gate -- declared in `thresholds.py` but never
populated by any benchmark run until `schema_validity_benchmark.py`).

Deliberately just `(query_id, query)` pairs, not a `GoldenExample`-shaped
dataset: this benchmark measures whether the model's *raw output*
conforms to a structured-output schema, not answer quality -- there is
no reference answer, rubric, or context to check against, so reusing
`golden_dataset.py`'s schema here would carry a dozen unused fields.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class SchemaValidityQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query_id: str

    query: str


class SchemaValidityDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str

    notes: str = ""

    queries: list[SchemaValidityQuery]


def load_schema_validity_dataset(path: Path) -> SchemaValidityDataset:
    """
    Raises:
        FileNotFoundError:
            If the dataset file does not exist.
    """

    if not path.exists():
        raise FileNotFoundError(f"Schema validity dataset not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    return SchemaValidityDataset.model_validate(payload)


__all__ = [
    "SchemaValidityDataset",
    "SchemaValidityQuery",
    "load_schema_validity_dataset",
]
