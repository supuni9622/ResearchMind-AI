import type { ResearchTurn, StreamStage, RetrievalStrategy } from '@/features/research/types';
import { STREAM_STAGES } from '@/features/research/types';

const STRATEGIES: RetrievalStrategy[] = ['dense', 'sparse', 'hybrid', 'reranked'];

const MOCK_DOCS = ['llm-paper.pdf', 'rag-survey.pdf', 'evaluation-methods.pdf', 'agentic-systems.pdf'];

function mockSources(question: string) {
  const count = 2 + (question.length % 3);
  return Array.from({ length: count }, (_, i) => ({
    citationId: i + 1,
    documentName: MOCK_DOCS[i % MOCK_DOCS.length],
    pages: `${3 + i * 2}–${5 + i * 2}`,
    score: Math.round((0.94 - i * 0.07) * 100) / 100,
    strategy: STRATEGIES[i % STRATEGIES.length],
    excerpt:
      'A relevant excerpt from the source document that supports the claim in the answer would appear here, drawn directly from the retrieved chunk.',
  }));
}

export async function runResearchTurn(
  question: string,
  onStage: (stage: StreamStage) => void
): Promise<ResearchTurn> {
  for (const stage of STREAM_STAGES) {
    onStage(stage);
    await new Promise((r) => setTimeout(r, 380));
  }

  const sources = mockSources(question);

  return {
    id: crypto.randomUUID(),
    question,
    planSteps: [
      { id: 'p1', label: `Identify documents relevant to "${question.slice(0, 40)}${question.length > 40 ? '…' : ''}"` },
      { id: 'p2', label: 'Retrieve and rank supporting passages' },
      { id: 'p3', label: 'Synthesize a grounded answer with citations' },
    ],
    sources,
    answer: `This is where your AI-generated answer to "${question}" will appear — grounded in your uploaded documents with inline citations [¹] for each claim drawn from a specific source. Connect the Generation Platform to replace this placeholder.`,
    evaluation: {
      groundedness: Math.round((0.8 + Math.random() * 0.15) * 100) / 100,
      faithfulness: Math.round((0.8 + Math.random() * 0.15) * 100) / 100,
    },
    metrics: {
      latencyMs: Math.round(1200 + Math.random() * 900),
      tokens: Math.round(400 + Math.random() * 600),
      costUsd: Math.round((0.002 + Math.random() * 0.006) * 1000) / 1000,
    },
    createdAt: new Date().toISOString(),
  };
}
