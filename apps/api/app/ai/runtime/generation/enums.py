from __future__ import annotations

from enum import StrEnum


class GenerationProvider(StrEnum):
    GROQ = "groq"
    OPENAI = "openai"
    CLAUDE = "claude"
    GEMINI = "gemini"
    OLLAMA = "ollama"


class GenerationOperation(StrEnum):
    GENERATE = "generate"

    GENERATE_STRUCTURED = "generate_structured"

    STREAM = "stream"


class ResponseFormat(StrEnum):
    TEXT = "text"

    JSON = "json"

    MARKDOWN = "markdown"

    XML = "xml"

    STRUCTURED = "structured"


class PromptStrategy(StrEnum):
    ZERO_SHOT = "zero_shot"

    FEW_SHOT = "few_shot"

    CHAIN_OF_THOUGHT = "chain_of_thought"

    REACT = "react"
