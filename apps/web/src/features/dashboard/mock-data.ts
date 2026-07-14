export interface ResearchSessionSummary {
  id: string;
  title: string;
  questionCount: number;
  documentCount: number;
  updatedAt: string;
}

export const RECENT_SESSIONS: ResearchSessionSummary[] = [
  { id: 'climate-research', title: 'Climate Research', questionCount: 12, documentCount: 8, updatedAt: '2026-07-13T15:20:00Z' },
  { id: 'llm-research', title: 'LLM Research', questionCount: 27, documentCount: 15, updatedAt: '2026-07-12T09:05:00Z' },
  { id: 'agentic-systems', title: 'Agentic Systems', questionCount: 6, documentCount: 4, updatedAt: '2026-07-10T18:40:00Z' },
];

export interface RecentQuestion {
  id: string;
  question: string;
  sessionTitle: string;
  askedAt: string;
}

export const RECENT_QUESTIONS: RecentQuestion[] = [
  {
    id: 'q1',
    question: 'What retrieval strategies outperform dense-only search on long documents?',
    sessionTitle: 'LLM Research',
    askedAt: '2026-07-13T16:02:00Z',
  },
  {
    id: 'q2',
    question: 'Summarize the projected sea level rise scenarios across all uploaded reports.',
    sessionTitle: 'Climate Research',
    askedAt: '2026-07-13T11:44:00Z',
  },
  {
    id: 'q3',
    question: 'How do the papers define groundedness versus faithfulness?',
    sessionTitle: 'Agentic Systems',
    askedAt: '2026-07-10T18:12:00Z',
  },
];

export interface SuggestedResearch {
  id: string;
  prompt: string;
  reason: string;
}

export const SUGGESTED_RESEARCH: SuggestedResearch[] = [
  {
    id: 's1',
    prompt: 'Compare methodology across your three most recently uploaded papers.',
    reason: 'New uploads detected',
  },
  {
    id: 's2',
    prompt: 'What open questions remain unanswered in the LLM Research session?',
    reason: 'Session has unresolved threads',
  },
  {
    id: 's3',
    prompt: 'Draft a synthesis report for Climate Research.',
    reason: 'Ready for report generation',
  },
];

export type ServiceStatus = 'operational' | 'degraded' | 'offline' | 'pending';

export interface PlatformService {
  id: string;
  label: string;
  detail: string;
  status: ServiceStatus;
}

export const STATIC_SERVICES: PlatformService[] = [
  { id: 'qdrant', label: 'Qdrant', detail: 'Vector store · :6333', status: 'operational' },
  { id: 'ai-engine', label: 'AI Engine', detail: 'Generation platform', status: 'pending' },
  { id: 'llm-providers', label: 'LLM Providers', detail: 'Groq · OpenAI · Claude', status: 'pending' },
];
