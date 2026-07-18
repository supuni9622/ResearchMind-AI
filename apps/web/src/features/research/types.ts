import type { Citation, GenerationProvider, ResearchSource } from '@/lib/api';

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

export interface ResearchHistoryEntry {
  researchId: string;
  query: string;
  createdAt: string;
}

export const PROVIDER_OPTIONS: { value: GenerationProvider | 'auto'; label: string }[] = [
  { value: 'auto', label: 'Auto' },
  { value: 'claude', label: 'Claude' },
  { value: 'openai', label: 'OpenAI' },
  { value: 'gemini', label: 'Gemini' },
  { value: 'groq', label: 'Groq' },
];
