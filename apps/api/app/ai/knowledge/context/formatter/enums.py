from enum import StrEnum


class PromptFormatStrategy(
    StrEnum,
):
    DEFAULT = "default"

    NOTEBOOKLM = "notebooklm"

    PERPLEXITY = "perplexity"

    RESEARCH = "research"

    AGENT = "agent"
