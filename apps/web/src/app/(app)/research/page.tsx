'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { GenerationProvider } from '@/lib/api';
import { useResearch } from '@/features/research/use-research';
import { ResearchSidebar } from '@/features/research/components/research-sidebar';
import { ResearchBlock } from '@/features/research/components/research-block';
import { ResearchComposer } from '@/features/research/components/research-composer';
import { SourcePanel } from '@/features/research/components/source-panel';
import { EmptyWorkspace } from '@/features/research/components/empty-workspace';

export default function ResearchPage() {
  const { turns, history, ask, loadFromHistory, clearWorkspace } = useResearch();
  const [focusedTurnId, setFocusedTurnId] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [provider, setProvider] = useState<GenerationProvider | 'auto'>('auto');
  const bottomRef = useRef<HTMLDivElement>(null);

  const loading = turns.some((t) => t.stage === 'searching' || t.stage === 'generating');

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const sessionParam = params.get('session');
    const qParam = params.get('q');
    if (qParam) setInput(qParam);
    if (sessionParam) {
      loadFromHistory(sessionParam).then(setFocusedTurnId);
    }
    // Only ever run once, on mount — replaying a URL param shouldn't refire on state changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [turns.length]);

  const focusedTurn = useMemo(
    () => turns.find((t) => t.localId === focusedTurnId) ?? turns[turns.length - 1] ?? null,
    [turns, focusedTurnId]
  );

  const handleSubmit = useCallback(() => {
    const query = input.trim();
    if (!query || loading) return;
    setInput('');
    const localId = ask(query, provider === 'auto' ? undefined : provider);
    setFocusedTurnId(localId);
  }, [input, loading, ask, provider]);

  function handleSelectHistory(researchId: string) {
    loadFromHistory(researchId).then(setFocusedTurnId);
  }

  return (
    <div className="flex h-screen">
      <ResearchSidebar
        history={history}
        activeResearchId={focusedTurn?.researchId ?? null}
        onSelect={handleSelectHistory}
        onClear={() => {
          clearWorkspace();
          setFocusedTurnId(null);
        }}
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
            Research
          </h1>
        </div>

        <div className="flex-1 overflow-y-auto px-8 py-6 scrollbar-thin">
          {turns.length === 0 ? (
            <EmptyWorkspace onSuggest={setInput} />
          ) : (
            <div className="max-w-2xl space-y-4">
              {turns.map((turn) => (
                <ResearchBlock
                  key={turn.localId}
                  turn={turn}
                  focused={focusedTurn?.localId === turn.localId}
                  onFocus={() => setFocusedTurnId(turn.localId)}
                />
              ))}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        <ResearchComposer
          value={input}
          onChange={setInput}
          onSubmit={handleSubmit}
          loading={loading}
          provider={provider}
          onProviderChange={setProvider}
        />
      </div>

      <SourcePanel turn={focusedTurn} />
    </div>
  );
}
