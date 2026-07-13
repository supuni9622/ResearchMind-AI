from __future__ import annotations

from pydantic import BaseModel


class FusionResult(BaseModel):
    chunk_id: str

    score: float

    dense_rank: int | None = None

    sparse_rank: int | None = None
