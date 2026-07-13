from __future__ import annotations

from pydantic import BaseModel


class DenseQueryEmbedding(BaseModel):
    vector: list[float]


class SparseQueryEmbedding(BaseModel):
    indices: list[int]

    values: list[float]
