'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { api, type GenerationProvider, type ResearchEscalationCheck } from '@/lib/api';
import { useResearch } from '@/features/research/use-research';
import { useDeepResearch } from '@/features/research/use-deep-research';
import type {
  ResearchMode,
  ResearchTurn,
  DeepResearchTurn,
  DeepResearchWebSearchMode,
} from '@/features/research/types';
import { ResearchSidebar } from '@/features/research/components/research-sidebar';
import { ResearchBlock } from '@/features/research/components/research-block';
import { DeepResearchBlock } from '@/features/research/components/deep-research-block';
import { EscalationSuggestion } from '@/features/research/components/escalation-suggestion';
import { ResearchComposer } from '@/features/research/components/research-composer';
import { SourcePanel } from '@/features/research/components/source-panel';
import { EmptyWorkspace } from '@/features/research/components/empty-workspace';
import { useActiveProject } from '@/hooks/use-active-project';

type FeedItem =
  | { type: 'linear'; turn: ResearchTurn }
  | { type: 'deep'; turn: DeepResearchTurn };

// Mirrors `features/dashboard/components/kb-stats.tsx`'s cost formatting --
// generation costs are often sub-cent, so up to 4 fraction digits.
const formatCost = (cost: number) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(cost);

export default function ResearchPage() {
  const { activeProjectId } = useActiveProject();
  const {
    turns,
    conversations,
    activeConversationId,
    setActiveConversationId,
    refreshConversations,
    conversationCost,
    ask,
    selectConversation,
    loadFromHistory,
    newConversation,
  } = useResearch();
  // Deep Research proposals/runs can reveal a `conversation_id` (their own,
  // or one already known from a Linear Research turn) -- feed it back into
  // the same shared conversation state so a session mixing both turn types
  // stays one conversation instead of forking a new one every deep-research
  // call (see `use-deep-research.ts`'s `learnConversationId`). Memoized so
  // `useDeepResearch`'s callbacks that depend on it don't get torn down and
  // rebuilt on every render.
  const onDeepResearchConversationLearned = useCallback(
    (conversationId: string) => {
      setActiveConversationId(conversationId);
      void refreshConversations();
    },
    [setActiveConversationId, refreshConversations]
  );
  const deepResearch = useDeepResearch(onDeepResearchConversationLearned);
  const [focusedTurnId, setFocusedTurnId] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [provider, setProvider] = useState<GenerationProvider | 'auto'>('auto');
  const [mode, setMode] = useState<ResearchMode>('linear');
  // Deep Research only (web_search_tool_platform_prd.md) -- Linear Research
  // has no runtime graph/interrupt machinery to act on these.
  const [webSearchMode, setWebSearchMode] = useState<DeepResearchWebSearchMode>('disabled');
  const [webSearchAutoApprove, setWebSearchAutoApprove] = useState(false);
  const [paperSuggestionsEnabled, setPaperSuggestionsEnabled] = useState(false);
  const [checkingEscalation, setCheckingEscalation] = useState(false);
  const [creatingProposal, setCreatingProposal] = useState(false);
  const [pendingEscalation, setPendingEscalation] = useState<{
    query: string;
    check: ResearchEscalationCheck;
  } | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [hasDocuments, setHasDocuments] = useState<boolean | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const linearLoading = turns.some((t) => t.stage === 'searching' || t.stage === 'generating');
  const loading = linearLoading || checkingEscalation || creatingProposal || pendingEscalation !== null;

  useEffect(() => {
    // Best-effort only -- used purely to steer the empty-state copy
    // ("upload something first" vs "you'll still get an answer"), never to
    // gate submission. A failure here shouldn't affect the rest of the page.
    let cancelled = false;
    api.documents
      .list({ limit: 1 })
      .then((res) => {
        if (!cancelled) setHasDocuments(res.total > 0);
      })
      .catch(() => {
        if (!cancelled) setHasDocuments(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

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
      void deepResearch.hydrateFromConversation(conversationParam);
    }
    // Only ever run once, on mount — replaying a URL param shouldn't refire on state changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Keep the URL in sync with whichever conversation is active so a plain
  // refresh (not just an explicit `?conversation=` link) reloads via the
  // mount effect above instead of landing on an empty workspace -- this is
  // what makes a Deep Research run (or a mixed linear+deep session) survive
  // a refresh in the common case, not just when the URL already names it.
  useEffect(() => {
    if (!activeConversationId) return;
    const params = new URLSearchParams(window.location.search);
    if (params.get('conversation') === activeConversationId) return;
    params.set('conversation', activeConversationId);
    params.delete('session');
    params.delete('q');
    window.history.replaceState(null, '', `${window.location.pathname}?${params.toString()}`);
  }, [activeConversationId]);

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
          projectId: activeConversationId ? undefined : activeProjectId,
          webSearchMode,
          webSearchAutoApprove,
          paperSuggestionsEnabled,
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
        projectId: activeConversationId ? undefined : activeProjectId,
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
  }, [
    input,
    loading,
    mode,
    provider,
    activeConversationId,
    activeProjectId,
    deepResearch,
    ask,
    webSearchMode,
    webSearchAutoApprove,
    paperSuggestionsEnabled,
  ]);

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
    void deepResearch.hydrateFromConversation(conversationId);
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
          const params = new URLSearchParams(window.location.search);
          params.delete('conversation');
          params.delete('session');
          params.delete('q');
          const query = params.toString();
          window.history.replaceState(null, '', query ? `${window.location.pathname}?${query}` : window.location.pathname);
        }}
      />

      <div className="flex-1 min-w-0 flex flex-col">
        <div className="px-8 pt-6 pb-4 border-b border-ink-600 flex-shrink-0">
          <div className="flex items-start justify-between gap-4">
            <div>
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
              <p className="text-stone-500 text-[12px] mt-1">
                {mode === 'deep'
                  ? 'Multi-step agentic research — plan, evidence, and report each need your approval before the run continues. Web and paper search available.'
                  : 'Grounded in your uploaded documents only — a fast, cited, one-shot answer. No web or paper search here.'}
              </p>
            </div>

            {conversationCost && conversationCost.total_requests > 0 && (
              <div
                className="flex-shrink-0 text-right"
                title="Estimated generation cost for this conversation's Linear Research turns. Deep Research runs are billed separately and aren't included here."
              >
                <p className="font-mono text-stone-600 text-[10px] tracking-[0.2em] uppercase mb-1">
                  Conversation Cost
                </p>
                <p className="font-display text-stone-300 text-[15px]">
                  {formatCost(conversationCost.total_cost_usd)}
                </p>
              </div>
            )}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-8 py-6 scrollbar-thin">
          {feed.length === 0 ? (
            <EmptyWorkspace mode={mode} hasDocuments={hasDocuments} onSuggest={setInput} />
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
                    onRetry={() =>
                      item.turn.run &&
                      deepResearch.retry(item.turn.localId, item.turn.run.research_run_id)
                    }
                    onPlanDecision={(approved, reason, editedGoal) =>
                      item.turn.run &&
                      deepResearch.submitPlanDecision(
                        item.turn.localId,
                        item.turn.run.research_run_id,
                        approved,
                        reason,
                        editedGoal
                      )
                    }
                    onReportDecision={(approved, reason, editedDraft) =>
                      item.turn.run &&
                      deepResearch.submitReportDecision(
                        item.turn.localId,
                        item.turn.run.research_run_id,
                        approved,
                        reason,
                        editedDraft
                      )
                    }
                    onWebSearchDecision={(approved, reason) =>
                      item.turn.run &&
                      deepResearch.submitWebSearchDecision(
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
          webSearchMode={webSearchMode}
          onWebSearchModeChange={setWebSearchMode}
          webSearchAutoApprove={webSearchAutoApprove}
          onWebSearchAutoApproveChange={setWebSearchAutoApprove}
          paperSuggestionsEnabled={paperSuggestionsEnabled}
          onPaperSuggestionsEnabledChange={setPaperSuggestionsEnabled}
        />
      </div>

      <SourcePanel turn={focusedLinearTurn} />
    </div>
  );
}
