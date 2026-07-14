"""
Reranking configuration models.
"""

from pydantic import BaseModel, ConfigDict, Field


class CrossEncoderConfig(
    BaseModel,
):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    model: str = Field(
        default="BAAI/bge-reranker-base",
    )


class VoyageRerankerConfig(
    BaseModel,
):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    model: str = Field(
        default="rerank-2",
    )
