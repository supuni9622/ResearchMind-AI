from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class SourceType(StrEnum):
    ACADEMIC = "academic"

    JOURNAL = "journal"

    NEWS = "news"

    BLOG = "blog"

    FORUM = "forum"

    USER_DOCUMENT = "user_document"

    WEB = "web"


class SourceTrust(
    BaseModel,
):
    model_config = ConfigDict(
        extra="forbid",
    )

    source_type: SourceType

    trust_score: float

    peer_reviewed: bool = False

    publisher: str | None = None

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )
