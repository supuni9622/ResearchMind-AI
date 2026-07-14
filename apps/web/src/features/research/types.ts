export type RetrievalStrategy = 'dense' | 'sparse' | 'hybrid' | 'reranked';

export interface SourceRef {
  citationId: number;
  documentName: string;
  pages: string;
  score: number;
  strategy: RetrievalStrategy;
  excerpt: string;
}

export interface PlanStep {
  id: string;
  label: string;
}

export interface EvaluationScores {
  groundedness: number;
  faithfulness: number;
}

export interface ResearchMetrics {
  latencyMs: number;
  tokens: number;
  costUsd: number;
}

export interface ResearchTurn {
  id: string;
  question: string;
  planSteps: PlanStep[];
  sources: SourceRef[];
  answer: string;
  evaluation: EvaluationScores;
  metrics: ResearchMetrics;
  createdAt: string;
}

export interface ResearchSessionMeta {
  id: string;
  title: string;
  updatedAt: string;
}

export const STREAM_STAGES = [
  'Retrieving documents…',
  'Expanding context…',
  'Compressing sources…',
  'Generating answer…',
  'Evaluating answer…',
] as const;

export type StreamStage = (typeof STREAM_STAGES)[number];
