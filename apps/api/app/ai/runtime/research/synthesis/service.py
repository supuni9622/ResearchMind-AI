"""Generation Runtime-only synthesis from bounded evidence references."""

from __future__ import annotations

from uuid import UUID

import structlog

from app.ai.knowledge.context.models import PromptContext
from app.ai.runtime.generation.caching.enums import CacheRuntime
from app.ai.runtime.generation.config_fingerprint import config_fingerprint_kwargs
from app.ai.runtime.generation.enums import GenerationProvider, ResponseFormat
from app.ai.runtime.generation.models import GenerationRequest
from app.ai.runtime.generation.orchestration.interfaces import GenerationRuntimeInterface
from app.ai.runtime.generation.routing.enums import RoutingStrategy
from app.ai.runtime.generation.validation.runtime.enums import RuntimeType
from app.ai.runtime.research.evidence import ResearchEvidenceBundle
from app.ai.runtime.research.synthesis.models import ResearchDraft

logger = structlog.get_logger()


class ResearchSynthesisError(ValueError):
    pass


class ResearchSynthesisService:
    def __init__(self, generation_runtime: GenerationRuntimeInterface) -> None:
        self._generation_runtime = generation_runtime

    async def synthesize(
        self,
        *,
        goal: str,
        evidence: ResearchEvidenceBundle,
        owner_id: UUID,
        research_run_id: UUID,
        provider: GenerationProvider | None = None,
        routing_strategy: RoutingStrategy | None = None,
        revision_instructions: list[str] | None = None,
    ) -> ResearchDraft:
        evidence_text = "\n".join(
            f"[{item.citation_id or 'uncited'}] {item.filename}: {item.excerpt}"
            for item in evidence.evidence
        )
        result = await self._generation_runtime.execute(
            GenerationRequest(
                prompt_context=PromptContext(context=evidence_text, chunks=[]),
                system_prompt=(
                    "Write a grounded standard research report using only supplied evidence. "
                    "Include a title, abstract, methodology (describe this evidence-based "
                    "research process), findings, discussion, conclusion, limitations, and "
                    "references via citation IDs. Return only the structured response; do not "
                    "invent citation IDs."
                ),
                user_prompt=(
                    f"Research goal: {goal}"
                    + (
                        "\n\nRevise the prior draft according to these requirements:\n- "
                        + "\n- ".join(revision_instructions)
                        if revision_instructions
                        else ""
                    )
                ),
                response_format=ResponseFormat.STRUCTURED,
                output_model=ResearchDraft,
                # `ResearchDraft`'s schema bounds (title 300 + abstract 2,000 +
                # methodology 2,000 + up to 8 `findings` sections of up to
                # 6,000 chars each + discussion 4,000 + conclusion 2,000 +
                # limitations) allow a fully-populated draft of ~60,000+
                # chars (~15,000-18,000 tokens). 2,000 was sized like the
                # planner's budget but for a schema an order of magnitude
                # smaller; confirmed in production truncating mid-JSON
                # (`finish_reason="max_tokens"`) on a real multi-finding
                # report, which then fails `ResearchDraft.model_validate()`
                # below with every required field missing. Sized generously
                # above the schema's theoretical worst case so a genuinely
                # long report never gets cut off.
                max_tokens=20_000,
                max_regeneration_attempts=1,
                owner_id=owner_id,
                session_id=research_run_id,
                routing_strategy=routing_strategy,
                # NEVER-cached (see CacheRuntime.REVIEWER's default policy) --
                # a semantic-cache hit here would silently substitute prose
                # written for a *different* run's evidence bundle into this
                # run's report. Deliberately not CacheRuntime.RESEARCH:
                # that's the shared, cached Linear Research answer namespace.
                cache_runtime=CacheRuntime.REVIEWER,
                runtime=RuntimeType.RESEARCH,
                metadata={
                    "research_run_id": str(research_run_id),
                    "prompt_version": "research-synthesis-v1",
                    "revision_requested": bool(revision_instructions),
                },
                **config_fingerprint_kwargs(
                    surface="deep_research", prompt_version="research-synthesis-v1"
                ),
            ),
            provider=provider,
        )
        try:
            draft = (
                result.parsed_output
                if isinstance(result.parsed_output, ResearchDraft)
                else ResearchDraft.model_validate(result.parsed_output)
            )
        except Exception as exc:
            logger.warning(
                "research_runtime.synthesis.schema_invalid",
                research_run_id=str(research_run_id),
            )
            raise ResearchSynthesisError("Synthesis did not return a schema-valid draft.") from exc

        draft = draft.model_copy(update={"generation_id": result.generation_id})

        allowed = set(evidence.citation_ids)
        used = set(draft.citation_ids)
        for section in draft.findings:
            used.update(section.citation_ids)
        unsupported = used - allowed
        if unsupported:
            logger.warning(
                "research_runtime.synthesis.unsupported_citations",
                research_run_id=str(research_run_id),
                unsupported_citation_ids=sorted(unsupported),
            )
            raise ResearchSynthesisError(
                f"Draft referenced unknown citation IDs: {sorted(unsupported)}."
            )
        return draft
