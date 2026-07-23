import type { Citation, DeepResearchProposal, DeepResearchRun, GenerationProvider, ResearchSource } from '@/lib/api';
export { PROVIDER_OPTIONS } from '@/lib/api';
export type {
  DeepResearchPlan,
  DeepResearchPlanTask,
  DeepResearchProposal,
  DeepResearchRun,
  DeepResearchRunStatus,
  ResearchComplexity,
  ResearchEscalationCheck,
} from '@/lib/api';

export type ResearchStage = 'searching' | 'generating' | 'done' | 'error';

/** Manual selector in the composer -- default is `linear`. */
export type ResearchMode = 'linear' | 'deep';

/**
 * Client-side view of where one Deep Research turn sits:
 * `plan_review` (awaiting approve/cancel) -> `running` (approved, polling
 * status) -> `report_review` (graph paused at the report-approval
 * interrupt) -> `done`/`failed`. `error` is a request-level failure
 * (network, etc.), distinct from a run reaching a terminal `failed`/
 * `cancelled` status.
 */
export type DeepResearchStage = 'plan_review' | 'running' | 'report_review' | 'done' | 'failed' | 'error';

/** One label from the live `GET /research/runs/{id}/events` SSE feed. */
export interface DeepResearchProgressEvent {
  type: string;
  label: string;
  timestamp: string;
}

export interface DeepResearchTurn {
  localId: string;
  query: string;
  /** Mirrors `proposal.created_at` -- used to interleave with `ResearchTurn.createdAt` in one chronological feed. */
  createdAt: string;
  proposal: DeepResearchProposal;
  run: DeepResearchRun | null;
  stage: DeepResearchStage;
  /** Ordered, oldest-first log of safe progress labels streamed live while `stage` is `running`/`report_review`. */
  events: DeepResearchProgressEvent[];
  reportDownloadUrl: string | null;
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
