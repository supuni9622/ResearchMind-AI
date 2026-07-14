from enum import StrEnum


class ChunkRiskLevel(
    StrEnum,
):
    SAFE = "safe"

    SUSPICIOUS = "suspicious"

    MALICIOUS = "malicious"
