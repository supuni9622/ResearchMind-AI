from enum import StrEnum


class CompressionStrategy(StrEnum):
    TOKEN_BUDGET = "token_budget"

    EMBEDDING_REDUNDANCY = "embedding_redundancy"

    LANGCHAIN_CONTEXTUAL = "langchain_contextual"

    LLM = "llm"
