import re

from app.ai.knowledge.context.guardrails.enums import (
    ChunkRiskLevel,
)
from app.ai.knowledge.context.guardrails.interfaces import (
    ContextGuardrailInterface,
)
from app.ai.knowledge.context.guardrails.models import (
    GuardrailResult,
    GuardrailStatistics,
)
from app.ai.knowledge.context.models import (
    ContextChunk,
)


class ContextGuardrailService(
    ContextGuardrailInterface,
):
    """
    Detect prompt injections
    and suspicious instructions.
    """

    PATTERNS = {
        "ignore_previous_instructions": r"ignore\s+.*instructions",
        "system_prompt": r"system\s+prompt",
        "developer_instructions": r"developer\s+instructions",
        "assistant_instructions": r"assistant\s+instructions",
        "reveal_hidden": r"reveal\s+.*prompt",
        "tool_call": r"tool\s+call",
        "function_call": r"function\s+call",
        "execute_code": r"execute\s+code",
        "browse": r"browse\s+the\s+internet",
        "send_email": r"send\s+email",
        "jailbreak": r"jailbreak",
    }

    async def validate(
        self,
        chunks: list[ContextChunk],
    ) -> GuardrailResult:

        warnings = []

        safe = 0
        suspicious = 0
        malicious = 0

        for chunk in chunks:
            content = chunk.content.lower()

            reasons = []

            for (
                name,
                pattern,
            ) in self.PATTERNS.items():
                if re.search(
                    pattern,
                    content,
                ):
                    reasons.append(name)

            chunk.risk_reasons = reasons

            if not reasons:
                chunk.risk_level = ChunkRiskLevel.SAFE

                safe += 1

                continue

            if len(reasons) == 1:
                chunk.risk_level = ChunkRiskLevel.SUSPICIOUS

                suspicious += 1

            else:
                chunk.risk_level = ChunkRiskLevel.MALICIOUS

                malicious += 1

                warnings.append(f"Potential prompt injection detected in chunk {chunk.chunk_id}")

        return GuardrailResult(
            chunks=chunks,
            statistics=(
                GuardrailStatistics(
                    safe_chunks=safe,
                    suspicious_chunks=(suspicious),
                    malicious_chunks=(malicious),
                )
            ),
            warnings=warnings,
        )
