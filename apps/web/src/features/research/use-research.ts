'use client';

import { useCallback, useEffect, useState } from 'react';
import { api, type GenerationProvider } from '@/lib/api';
import type { ResearchHistoryEntry, ResearchStage, ResearchTurn } from '@/features/research/types';

const HISTORY_KEY = 'rm_research_history';
const HISTORY_LIMIT = 50;

function loadHistory(): ResearchHistoryEntry[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(HISTORY_KEY);
    return raw ? (JSON.parse(raw) as ResearchHistoryEntry[]) : [];
  } catch {
    return [];
  }
}

function saveHistory(entries: ResearchHistoryEntry[]): void {
  try {
    window.localStorage.setItem(HISTORY_KEY, JSON.stringify(entries.slice(0, HISTORY_LIMIT)));
  } catch {}
}

function emptyTurn(localId: string, query: string): ResearchTurn {
  return {
    localId,
    researchId: null,
    query,
    answer: '',
    citations: [],
    sources: [],
    stage: 'searching',
    createdAt: new Date().toISOString(),
  };
}

function patchTurn(
  turns: ResearchTurn[],
  localId: string,
  patch: Partial<ResearchTurn> | ((t: ResearchTurn) => Partial<ResearchTurn>)
): ResearchTurn[] {
  return turns.map((t) =>
    t.localId === localId ? { ...t, ...(typeof patch === 'function' ? patch(t) : patch) } : t
  );
}

export function useResearch() {
  const [turns, setTurns] = useState<ResearchTurn[]>([]);
  const [history, setHistory] = useState<ResearchHistoryEntry[]>([]);

  useEffect(() => {
    setHistory(loadHistory());
  }, []);

  const addHistoryEntry = useCallback((entry: ResearchHistoryEntry) => {
    setHistory((prev) => {
      const next = [entry, ...prev.filter((h) => h.researchId !== entry.researchId)];
      saveHistory(next);
      return next;
    });
  }, []);

  const runAsk = useCallback(
    async (localId: string, query: string, provider?: GenerationProvider) => {
      const startedAt = performance.now();
      let researchId: string | null = null;

      try {
        for await (const { data: event } of api.research.stream(query, { provider })) {
          if (event.session_id && !researchId) {
            researchId = event.session_id;
            setTurns((prev) => patchTurn(prev, localId, { researchId }));
          }

          if (event.type === 'retrieval_completed') {
            const chunkCount = event.metadata?.chunk_count as number | undefined;
            setTurns((prev) => patchTurn(prev, localId, { chunkCount }));
            continue;
          }

          if (event.type === 'token' && event.content) {
            setTurns((prev) =>
              patchTurn(prev, localId, (t) => ({
                stage: 'generating' as ResearchStage,
                answer: t.answer + event.content,
              }))
            );
            continue;
          }

          if (event.type === 'start') {
            setTurns((prev) => patchTurn(prev, localId, { stage: 'generating' }));
            continue;
          }

          if (event.type === 'error') {
            setTurns((prev) =>
              patchTurn(prev, localId, {
                stage: 'error',
                error: event.content ?? 'The research runtime returned an error.',
              })
            );
            return;
          }
        }

        const durationMs = Math.round(performance.now() - startedAt);

        if (researchId) {
          try {
            const session = await api.research.get(researchId);
            setTurns((prev) =>
              patchTurn(prev, localId, {
                stage: 'done',
                answer: session.answer,
                citations: session.citations,
                sources: session.sources,
                durationMs,
              })
            );
            addHistoryEntry({ researchId, query, createdAt: session.created_at });
            return;
          } catch {
            // Session replay failed (e.g. artifact/session persistence hiccup) —
            // fall through and keep the answer we already streamed.
          }
        }

        setTurns((prev) => patchTurn(prev, localId, { stage: 'done', durationMs }));
      } catch (err) {
        setTurns((prev) =>
          patchTurn(prev, localId, {
            stage: 'error',
            error: err instanceof Error ? err.message : 'Something went wrong.',
          })
        );
      }
    },
    [addHistoryEntry]
  );

  const ask = useCallback(
    (query: string, provider?: GenerationProvider): string => {
      const localId = crypto.randomUUID();
      setTurns((prev) => [...prev, emptyTurn(localId, query)]);
      void runAsk(localId, query, provider);
      return localId;
    },
    [runAsk]
  );

  const loadFromHistory = useCallback(
    async (researchId: string) => {
      const existing = turns.find((t) => t.researchId === researchId);
      if (existing) return existing.localId;

      const localId = crypto.randomUUID();
      setTurns((prev) => [...prev, { ...emptyTurn(localId, ''), researchId, stage: 'generating' }]);

      try {
        const session = await api.research.get(researchId);
        setTurns((prev) =>
          patchTurn(prev, localId, {
            query: session.query,
            answer: session.answer,
            citations: session.citations,
            sources: session.sources,
            stage: 'done',
            createdAt: session.created_at,
          })
        );
      } catch (err) {
        setTurns((prev) =>
          patchTurn(prev, localId, {
            stage: 'error',
            error: err instanceof Error ? err.message : 'Could not load this research session.',
          })
        );
      }

      return localId;
    },
    [turns]
  );

  const clearWorkspace = useCallback(() => setTurns([]), []);

  return { turns, history, ask, loadFromHistory, clearWorkspace };
}
