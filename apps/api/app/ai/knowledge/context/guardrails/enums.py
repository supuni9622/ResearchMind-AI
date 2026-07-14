from enum import StrEnum


class ChunkRiskLevel(
    StrEnum,
):
    SAFE = "safe"

    SUSPICIOUS = "suspicious"

    MALICIOUS = "malicious"


class GuardrailStrategy(
    StrEnum,
):
    RULE_BASED = "rule_based"

    LLAMA_GUARD = "llama_guard"

    NEMO = "nemo"

    LAKERA = "lakera"
