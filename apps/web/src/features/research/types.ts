import type { Citation, GenerationProvider, ResearchSource } from '@/lib/api';
export { PROVIDER_OPTIONS } from '@/lib/api';

export type ResearchStage = 'searching' | 'generating' | 'done' | 'error';

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
