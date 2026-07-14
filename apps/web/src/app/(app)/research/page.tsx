'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { ResearchSessionMeta, ResearchTurn, StreamStage } from '@/features/research/types';
import { runResearchTurn } from '@/features/research/mock-engine';
import { RECENT_SESSIONS } from '@/features/dashboard/mock-data';
import { ResearchSidebar } from '@/features/research/components/research-sidebar';
import { ResearchBlock } from '@/features/research/components/research-block';
import { ResearchComposer } from '@/features/research/components/research-composer';
import { StreamingStatus } from '@/features/research/components/streaming-status';
import { SourcePanel } from '@/features/research/components/source-panel';
import { EmptyWorkspace } from '@/features/research/components/empty-workspace';

const INITIAL_SESSIONS: ResearchSessionMeta[] = RECENT_SESSIONS.map((s) => ({
  id: s.id,
  title: s.title,
  updatedAt: s.updatedAt,
}));

export default function ResearchPage() {
  const [sessions, setSessions] = useState<ResearchSessionMeta[]>(INITIAL_SESSIONS);
  const [activeSessionId, setActiveSessionId] = useState(INITIAL_SESSIONS[0].id);
  const [turnsBySession, setTurnsBySession] = useState<Record<string, ResearchTurn[]>>({});
  const [focusedTurnId, setFocusedTurnId] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState<StreamStage | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const sessionParam = params.get('session');
    const qParam = params.get('q');
    if (sessionParam && INITIAL_SESSIONS.some((s) => s.id === sessionParam)) {
      setActiveSessionId(sessionParam);
    }
    if (qParam) setInput(qParam);
  }, []);

  const turns = useMemo(
    () => turnsBySession[activeSessionId] ?? [],
    [turnsBySession, activeSessionId]
  );

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [turns.length, loading]);

  useEffect(() => {
    setFocusedTurnId(turns.length > 0 ? turns[turns.length - 1].id : null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeSessionId]);

  const focusedTurn = useMemo(
    () => turns.find((t) => t.id === focusedTurnId) ?? turns[turns.length - 1] ?? null,
    [turns, focusedTurnId]
  );

  const handleSubmit = useCallback(async () => {
    const question = input.trim();
    if (!question || loading) return;
    setInput('');
    setLoading(true);

    const turn = await runResearchTurn(question, setStage);

    setTurnsBySession((prev) => ({
      ...prev,
      [activeSessionId]: [...(prev[activeSessionId] ?? []), turn],
    }));
    setFocusedTurnId(turn.id);
    setLoading(false);
    setStage(null);
  }, [input, loading, activeSessionId]);

  function handleCreateSession() {
    const id = crypto.randomUUID();
    const title = `Untitled Session ${sessions.length + 1}`;
    setSessions((prev) => [{ id, title, updatedAt: new Date().toISOString() }, ...prev]);
    setActiveSessionId(id);
  }

  return (
    <div className="flex h-screen">
      <ResearchSidebar
        sessions={sessions}
        activeId={activeSessionId}
        onSelect={setActiveSessionId}
        onCreate={handleCreateSession}
      />

      <div className="flex-1 min-w-0 flex flex-col">
        <div className="px-8 pt-6 pb-4 border-b border-ink-600 flex-shrink-0">
          <p className="font-mono text-stone-600 text-[10px] tracking-[0.2em] uppercase mb-1">
            AI Research
          </p>
          <h1
            className="font-display text-stone-100"
            style={{
              fontSize: '1.5rem',
              fontVariationSettings: "'opsz' 32, 'SOFT' 0, 'WONK' 0",
            }}
          >
            {sessions.find((s) => s.id === activeSessionId)?.title ?? 'Research'}
          </h1>
        </div>

        <div className="flex-1 overflow-y-auto px-8 py-6 scrollbar-thin">
          {turns.length === 0 && !loading ? (
            <EmptyWorkspace onSuggest={setInput} />
          ) : (
            <div className="max-w-2xl space-y-4">
              {turns.map((turn) => (
                <ResearchBlock
                  key={turn.id}
                  turn={turn}
                  focused={focusedTurn?.id === turn.id}
                  onFocus={() => setFocusedTurnId(turn.id)}
                />
              ))}
              {loading && stage && <StreamingStatus currentStage={stage} />}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        <ResearchComposer value={input} onChange={setInput} onSubmit={handleSubmit} loading={loading} />
      </div>

      <SourcePanel turn={focusedTurn} />
    </div>
  );
}
