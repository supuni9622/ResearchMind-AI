from app.ai.knowledge.context.models import (
    ContextChunk,
)
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class GuardrailStatistics(
    BaseModel,
):
    model_config = ConfigDict(extra="forbid")

    safe_chunks: int = 0

    suspicious_chunks: int = 0

    malicious_chunks: int = 0


class GuardrailResult(
    BaseModel,
):
    model_config = ConfigDict(extra="forbid")

    chunks: list[ContextChunk]

    removed_chunks: list[ContextChunk] = Field(default_factory=list)

    warnings: list[str] = Field(default_factory=list)

    statistics: GuardrailStatistics
