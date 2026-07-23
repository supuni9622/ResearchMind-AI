'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { api, type GenerationProvider, type ResearchEscalationCheck } from '@/lib/api';
import { useResearch } from '@/features/research/use-research';
import { useDeepResearch } from '@/features/research/use-deep-research';
import type { ResearchMode, ResearchTurn, DeepResearchTurn } from '@/features/research/types';
import { ResearchSidebar } from '@/features/research/components/research-sidebar';
import { ResearchBlock } from '@/features/research/components/research-block';
import { DeepResearchBlock } from '@/features/research/components/deep-research-block';
import { EscalationSuggestion } from '@/features/research/components/escalation-suggestion';
import { ResearchComposer } from '@/features/research/components/research-composer';
import { SourcePanel } from '@/features/research/components/source-panel';
import { EmptyWorkspace } from '@/features/research/components/empty-workspace';

type FeedItem =
  | { type: 'linear'; turn: ResearchTurn }
  | { type: 'deep'; turn: DeepResearchTurn };

export default function ResearchPage() {
  const { turns, conversations, activeConversationId, ask, selectConversation, loadFromHistory, newConversation } =
    useResearch();
  const deepResearch = useDeepResearch();
  const [focusedTurnId, setFocusedTurnId] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [provider, setProvider] = useState<GenerationProvider | 'auto'>('auto');
  const [mode, setMode] = useState<ResearchMode>('linear');
  const [checkingEscalation, setCheckingEscalation] = useState(false);
  const [creatingProposal, setCreatingProposal] = useState(false);
  const [pendingEscalation, setPendingEscalation] = useState<{
    query: string;
    check: ResearchEscalationCheck;
  } | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const linearLoading = turns.some((t) => t.stage === 'searching' || t.stage === 'generating');
  const loading = linearLoading || checkingEscalation || creatingProposal || pendingEscalation !== null;

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const sessionParam = params.get('session');
    const conversationParam = params.get('conversation');
    const qParam = params.get('q');
    if (qParam) setInput(qParam);
    if (sessionParam) {
      loadFromHistory(sessionParam).then(setFocusedTurnId);
    }
    if (conversationParam) {
      selectConversation(conversationParam).then((mapped) => {
        setFocusedTurnId(mapped[mapped.length - 1]?.localId ?? null);
      });
    }
    // Only ever run once, on mount — replaying a URL param shouldn't refire on state changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const feed = useMemo<FeedItem[]>(() => {
    const items: FeedItem[] = [
      ...turns.map((turn): FeedItem => ({ type: 'linear', turn })),
      ...deepResearch.turns.map((turn): FeedItem => ({ type: 'deep', turn })),
    ];
    items.sort(
      (a, b) => new Date(a.turn.createdAt).getTime() - new Date(b.turn.createdAt).getTime()
    );
    return items;
  }, [turns, deepResearch.turns]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [feed.length]);

  const focusedItem = useMemo(() => {
    if (feed.length === 0) return null;
    return feed.find((item) => item.turn.localId === focusedTurnId) ?? feed[feed.length - 1];
  }, [feed, focusedTurnId]);

  const focusedLinearTurn = focusedItem?.type === 'linear' ? focusedItem.turn : null;

  const handleSubmit = useCallback(async () => {
    const query = input.trim();
    if (!query || loading) return;
    setInput('');
    setSubmitError(null);
    const providerOrUndefined = provider === 'auto' ? undefined : provider;

    if (mode === 'deep') {
      setCreatingProposal(true);
      try {
        const localId = await deepResearch.createProposal(query, {
          provider: providerOrUndefined,
          conversationId: activeConversationId ?? undefined,
        });
        if (localId) {
          setFocusedTurnId(localId);
        } else {
          setSubmitError('Could not create the research proposal. Please try again.');
        }
      } finally {
        setCreatingProposal(false);
      }
      return;
    }

    setCheckingEscalation(true);
    try {
      const check = await api.research.checkEscalation(query, {
        provider: providerOrUndefined,
        conversationId: activeConversationId ?? undefined,
      });
      if (check.suggested && check.proposal) {
        setPendingEscalation({ query, check });
        return;
      }
    } catch {
      // Best-effort: if the escalation check itself fails, fall through to
      // Linear Research rather than blocking the user's question.
    } finally {
      setCheckingEscalation(false);
    }

    const localId = ask(query, providerOrUndefined);
    setFocusedTurnId(localId);
  }, [input, loading, mode, provider, activeConversationId, deepResearch, ask]);

  const handleAcceptEscalation = useCallback(() => {
    if (!pendingEscalation?.check.proposal) return;
    const localId = deepResearch.startFromProposal(
      pendingEscalation.query,
      pendingEscalation.check.proposal
    );
    setFocusedTurnId(localId);
    setPendingEscalation(null);
  }, [pendingEscalation, deepResearch]);

  const handleRejectEscalation = useCallback(() => {
    if (!pendingEscalation) return;
    const { query } = pendingEscalation;
    setPendingEscalation(null);
    const localId = ask(query, provider === 'auto' ? undefined : provider);
    setFocusedTurnId(localId);
  }, [pendingEscalation, ask, provider]);

  function handleSelectConversation(conversationId: string) {
    selectConversation(conversationId).then((mapped) => {
      setFocusedTurnId(mapped[mapped.length - 1]?.localId ?? null);
    });
  }

  return (
    <div className="flex h-screen">
      <ResearchSidebar
        conversations={conversations}
        activeConversationId={activeConversationId}
        onSelect={handleSelectConversation}
        onNew={() => {
          newConversation();
          deepResearch.reset();
          setPendingEscalation(null);
          setSubmitError(null);
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
          {feed.length === 0 ? (
            <EmptyWorkspace onSuggest={setInput} />
          ) : (
            <div className="max-w-2xl space-y-4">
              {feed.map((item) =>
                item.type === 'linear' ? (
                  <ResearchBlock
                    key={item.turn.localId}
                    turn={item.turn}
                    focused={focusedItem?.turn.localId === item.turn.localId}
                    onFocus={() => setFocusedTurnId(item.turn.localId)}
                  />
                ) : (
                  <DeepResearchBlock
                    key={item.turn.localId}
                    turn={item.turn}
                    focused={focusedItem?.turn.localId === item.turn.localId}
                    onFocus={() => setFocusedTurnId(item.turn.localId)}
                    onApprove={() =>
                      deepResearch.approve(item.turn.localId, item.turn.proposal.proposal_id)
                    }
                    onCancel={() =>
                      item.turn.run
                        ? deepResearch.cancel(item.turn.localId, item.turn.run.research_run_id)
                        : deepResearch.dismiss(item.turn.localId)
                    }
                    onReportDecision={(approved, reason) =>
                      item.turn.run &&
                      deepResearch.submitReportDecision(
                        item.turn.localId,
                        item.turn.run.research_run_id,
                        approved,
                        reason
                      )
                    }
                  />
                )
              )}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        {pendingEscalation && (
          <div className="px-8">
            <EscalationSuggestion
              check={pendingEscalation.check}
              loading={false}
              onAccept={handleAcceptEscalation}
              onReject={handleRejectEscalation}
            />
          </div>
        )}

        {submitError && (
          <p className="px-8 pb-2 font-mono text-[11px] text-red-400">{submitError}</p>
        )}

        {checkingEscalation && (
          <p className="px-8 pb-2 font-mono text-[10px] text-stone-600 uppercase tracking-widest">
            Checking the best approach…
          </p>
        )}

        <ResearchComposer
          value={input}
          onChange={setInput}
          onSubmit={() => void handleSubmit()}
          loading={loading}
          provider={provider}
          onProviderChange={setProvider}
          mode={mode}
          onModeChange={setMode}
        />
      </div>

      <SourcePanel turn={focusedLinearTurn} />
    </div>
  );
}
