'use client';

import { useCallback, useEffect, useState } from 'react';
import { api, type GenerationProvider, type ResearchSessionResponse } from '@/lib/api';
import type {
  ResearchConversationEntry,
  ResearchStage,
  ResearchTurn,
} from '@/features/research/types';

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

function turnFromSession(session: ResearchSessionResponse): ResearchTurn {
  return {
    localId: crypto.randomUUID(),
    researchId: session.research_id,
    query: session.query,
    answer: session.answer,
    citations: session.citations,
    sources: session.sources,
    stage: 'done',
    createdAt: session.created_at,
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
  const [conversations, setConversations] = useState<ResearchConversationEntry[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);

  const refreshConversations = useCallback(async () => {
    try {
      const { conversations: rows } = await api.research.listConversations();
      setConversations(
        rows.map((c) => ({
          conversationId: c.conversation_id,
          title: c.title ?? 'Untitled',
          updatedAt: c.updated_at,
        }))
      );
    } catch {
      // History sidebar is best-effort -- a failed refresh just leaves the
      // previous list in place rather than blocking the research turn.
    }
  }, []);

  useEffect(() => {
    void refreshConversations();
  }, [refreshConversations]);

  const runAsk = useCallback(
    async (localId: string, query: string, conversationIdAtStart: string | null, provider?: GenerationProvider) => {
      const startedAt = performance.now();
      let researchId: string | null = null;

      try {
        for await (const { data: event } of api.research.stream(query, {
          provider,
          conversationId: conversationIdAtStart ?? undefined,
        })) {
          if (event.session_id && !researchId) {
            researchId = event.session_id;
            setTurns((prev) => patchTurn(prev, localId, { researchId }));
          }

          if (!conversationIdAtStart && event.metadata?.conversation_id) {
            // First turn of a brand new conversation -- learn its
            // server-assigned id so the *next* `ask()` continues this
            // same thread instead of starting another one.
            setActiveConversationId(event.metadata.conversation_id as string);
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
            void refreshConversations();
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
    [refreshConversations]
  );

  const ask = useCallback(
    (query: string, provider?: GenerationProvider): string => {
      const localId = crypto.randomUUID();
      setTurns((prev) => [...prev, emptyTurn(localId, query)]);
      void runAsk(localId, query, activeConversationId, provider);
      return localId;
    },
    [runAsk, activeConversationId]
  );

  /** Loads a whole thread and returns its mapped turns (newest last), for callers that need to pick a specific turn out of it. */
  const selectConversation = useCallback(async (conversationId: string): Promise<ResearchTurn[]> => {
    try {
      const conversation = await api.research.getConversation(conversationId);
      const mapped = conversation.turns.map(turnFromSession);
      setTurns(mapped);
      setActiveConversationId(conversation.conversation_id);
      return mapped;
    } catch {
      return [];
    }
  }, []);

  const loadFromHistory = useCallback(
    async (researchId: string) => {
      const existing = turns.find((t) => t.researchId === researchId);
      if (existing) return existing.localId;

      try {
        const session = await api.research.get(researchId);

        if (session.conversation_id) {
          const mapped = await selectConversation(session.conversation_id);
          const matched = mapped.find((t) => t.researchId === researchId);
          return matched?.localId ?? mapped[mapped.length - 1]?.localId ?? null;
        }

        const localId = crypto.randomUUID();
        setTurns((prev) => [...prev, { ...turnFromSession(session), localId }]);
        return localId;
      } catch (err) {
        const localId = crypto.randomUUID();
        setTurns((prev) => [
          ...prev,
          {
            ...emptyTurn(localId, ''),
            stage: 'error',
            error: err instanceof Error ? err.message : 'Could not load this research session.',
          },
        ]);
        return localId;
      }
    },
    [turns, selectConversation]
  );

  const newConversation = useCallback(() => {
    setActiveConversationId(null);
    setTurns([]);
  }, []);

  return {
    turns,
    conversations,
    activeConversationId,
    ask,
    selectConversation,
    loadFromHistory,
    newConversation,
  };
}
