from pydantic import BaseModel


class Citation(
    BaseModel,
):
    source: str

    quote: str | None = None


class CitationCollection(
    BaseModel,
):
    citations: list[Citation]
