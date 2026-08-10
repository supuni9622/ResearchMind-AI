import type {
  Citation,
  DeepResearchDraft,
  DeepResearchPendingPlan,
  DeepResearchPendingWebSearch,
  DeepResearchProposal,
  DeepResearchRun,
  GenerationProvider,
  ResearchSource,
} from '@/lib/api';
export { PROVIDER_OPTIONS } from '@/lib/api';
export type {
  DeepResearchAskOptions,
  DeepResearchDraft,
  DeepResearchDraftEdit,
  DeepResearchPendingPlan,
  DeepResearchPendingPlanEvidence,
  DeepResearchPendingPlanTask,
  DeepResearchPendingWebSearch,
  DeepResearchPlan,
  DeepResearchPlanTask,
  DeepResearchProposal,
  DeepResearchRun,
  DeepResearchRunStatus,
  DeepResearchWebSearchMode,
  ResearchComplexity,
  ResearchEscalationCheck,
} from '@/lib/api';

export type ResearchStage = 'searching' | 'generating' | 'done' | 'error';

/** Manual selector in the composer -- default is `linear`. */
export type ResearchMode = 'linear' | 'deep';

/** True for a web-search-sourced citation. Derived from the ID scheme
 * itself rather than a separate field: document citations are `S{n}`
 * (`app/ai/knowledge/context/citations/service.py`), web citations are
 * `W{round}-{n}` (`app/ai/runtime/research/web_search/evidence.py`) --
 * Linear Research never produces a `W`-prefixed ID, since it has no web
 * search, so this is safe to apply to every citation list unconditionally. */
export function isWebCitation(citationId: string): boolean {
  return citationId.startsWith('W');
}

/**
 * Relevance percentage relative to the best score in the same list, not an
 * absolute scale. `Citation.score`/`ResearchSource.score` come from RRF
 * fusion (`app/ai/knowledge/retrieval/fusion/rrf.py`, k=60 across up to 3
 * ranked lists) -- its raw value tops out around 3-5% even for the best
 * possible match, so rendering it directly as `score * 100` reads as "weak"
 * no matter how relevant the result actually is. Normalizing against the
 * top score in the current answer's own list keeps the bar meaningful
 * (best match ~100%) regardless of what scale the backend's retrieval
 * strategy happens to produce.
 */
export function relativeScorePercent(score: number, maxScore: number): number {
  return maxScore > 0 ? Math.round((score / maxScore) * 100) : 0;
}

/**
 * Client-side view of where one Deep Research turn sits:
 * `plan_review` (awaiting approve/cancel, before a run exists at all) ->
 * `running` (approved, polling status) -> `goal_review` (graph paused at
 * the *plan*-approval interrupt -- reached after retrieval/evidence-
 * aggregation but before the synthesis call; distinct from `plan_review`,
 * which happens before any run/retrieval exists) -> `running` again ->
 * `web_search_review` (graph paused at the *web-search*-approval interrupt --
 * only reached in AUTO mode without pre-approval) -> `running` again ->
 * `report_review` (graph paused at the *report*-approval interrupt) ->
 * `done`/`failed`. `error` is a request-level failure (network, etc.),
 * distinct from a run reaching a terminal `failed`/`cancelled` status.
 */
export type DeepResearchStage =
  | 'plan_review'
  | 'running'
  | 'goal_review'
  | 'web_search_review'
  | 'report_review'
  | 'done'
  | 'failed'
  | 'error';

/** One label from the live `GET /research/runs/{id}/events` SSE feed. */
export interface DeepResearchProgressEvent {
  type: string;
  label: string;
  timestamp: string;
}

/** Carried on the `research_related_papers_completed` event's metadata --
 * a non-blocking, best-effort suggestion, never an approval checkpoint. */
export interface DeepResearchRelatedPaper {
  title: string;
  authors: string[];
  year: number | null;
  url: string | null;
}

/** The plain-text answer/citations a rejected report still publishes as
 * (see `run.terminal_reason === 'report_rejected_returned_as_answer'`) --
 * rejecting only skips the polished PDF, not the synthesized content. */
export interface DeepResearchLinearAnswer {
  answer: string;
  citations: Citation[];
}

export interface DeepResearchTurn {
  localId: string;
  query: string;
  /** Mirrors `proposal.created_at` -- used to interleave with `ResearchTurn.createdAt` in one chronological feed. */
  createdAt: string;
  proposal: DeepResearchProposal;
  run: DeepResearchRun | null;
  stage: DeepResearchStage;
  /** Ordered, oldest-first log of safe progress labels streamed live while `stage` is `running`/`goal_review`/`report_review`. */
  events: DeepResearchProgressEvent[];
  /** Fetched once `stage` reaches `goal_review` -- the plan and gathered evidence the approve/reject decision is about. */
  pendingPlan: DeepResearchPendingPlan | null;
  /** Fetched once `stage` reaches `web_search_review` -- the agent's web-search suggestion the approve/reject decision is about. */
  pendingWebSearch: DeepResearchPendingWebSearch | null;
  /** Fetched once `stage` reaches `report_review` -- the draft the approve/reject decision is about. */
  draft: DeepResearchDraft | null;
  reportDownloadUrl: string | null;
  /** Set instead of `reportDownloadUrl` when the report was rejected but still published as a plain answer. */
  linearAnswer: DeepResearchLinearAnswer | null;
  /** Populated from `research_related_papers_completed`'s metadata, if the
   * proposal opted in via `paperSuggestionsEnabled`. Non-blocking -- absent
   * whenever the toggle was off, MCP is unconfigured, or nothing was found. */
  relatedPapers: DeepResearchRelatedPaper[] | null;
  error?: string;
}

export interface ResearchTurn {
  /** Stable client-side key — assigned before the server hands back a research_id. */
  localId: string;
  /** `research_id` once the stream (or a non-streamed ask) has told us it. */
  researchId: string | null;
  query: string;
  answer: string;
  citations: Citation[];
  sources: ResearchSource[];
  stage: ResearchStage;
  error?: string;
  chunkCount?: number;
  durationMs?: number;
  provider?: GenerationProvider;
  createdAt: string;
}

/**
 * One "History" sidebar entry -- a whole conversation thread (possibly
 * many turns), not a single question. Server-backed via `GET
 * /research/conversations`, unlike Chat's localStorage-only history
 * (Chat has no server read path yet -- see `features/chat/use-chat.ts`).
 */
export interface ResearchConversationEntry {
  conversationId: string;
  /** Auto-set server-side from the thread's first question (`ResearchConversation.title`). */
  title: string;
  updatedAt: string;
}
