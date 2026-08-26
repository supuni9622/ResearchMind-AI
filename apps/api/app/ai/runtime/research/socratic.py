"""Model-assisted Socratic challenge generation for Deep Research."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.ai.knowledge.context.models import PromptContext
from app.ai.runtime.generation.caching.enums import CacheRuntime
from app.ai.runtime.generation.enums import ResponseFormat
from app.ai.runtime.generation.models import GenerationRequest
from app.ai.runtime.generation.orchestration.interfaces import GenerationRuntimeInterface
from app.ai.runtime.generation.validation.runtime.enums import RuntimeType
from app.ai.runtime.research.evidence import ResearchEvidenceBundle

SOCRATIC_CHALLENGER_PROMPT_VERSION = "socratic-challenger-v1"


class SocraticChallenge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=500)


class SocraticChallengerService:
    """Produce one bounded question that tests the researcher's assumptions."""

    MAX_EVIDENCE_ITEMS = 8
    MAX_EXCERPT_CHARACTERS = 300

    def __init__(self, generation_runtime: GenerationRuntimeInterface) -> None:
        self._generation_runtime = generation_runtime

    async def generate(
        self,
        *,
        goal: str,
        evidence: ResearchEvidenceBundle,
        owner_id: UUID,
        research_run_id: UUID,
    ) -> str:
        evidence_text = "\n".join(
            f"[{item.citation_id or 'uncited'}] {item.excerpt[: self.MAX_EXCERPT_CHARACTERS]}"
            for item in evidence.evidence[: self.MAX_EVIDENCE_ITEMS]
        )
        result = await self._generation_runtime.execute(
            GenerationRequest(
                prompt_context=PromptContext(context=evidence_text, chunks=[]),
                system_prompt=(
                    "You are a Socratic research challenger. Ask exactly one concise, "
                    "constructive question that exposes a consequential assumption, "
                    "alternative explanation, or missing perspective in the research goal. "
                    "Do not answer the question and do not invent evidence."
                ),
                user_prompt=(
                    f"Prompt version: {SOCRATIC_CHALLENGER_PROMPT_VERSION}\n"
                    f"Research goal: {goal}\n\nUse only the supplied evidence context."
                ),
                response_format=ResponseFormat.STRUCTURED,
                output_model=SocraticChallenge,
                max_tokens=180,
                max_regeneration_attempts=1,
                owner_id=owner_id,
                session_id=research_run_id,
                runtime=RuntimeType.REVIEWER,
                cache_runtime=CacheRuntime.REVIEWER,
                metadata={
                    "research_run_id": str(research_run_id),
                    "prompt_version": SOCRATIC_CHALLENGER_PROMPT_VERSION,
                },
            )
        )
        challenge = (
            result.parsed_output
            if isinstance(result.parsed_output, SocraticChallenge)
            else SocraticChallenge.model_validate(result.parsed_output)
        )
        return challenge.question
