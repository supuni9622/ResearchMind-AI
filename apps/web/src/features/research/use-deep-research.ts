'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  api,
  type DeepResearchAskOptions,
  type DeepResearchDraftEdit,
  type DeepResearchProposal,
  type DeepResearchRun,
} from '@/lib/api';
import type { DeepResearchStage, DeepResearchTurn } from '@/features/research/types';

const TERMINAL_RUN_STATUSES = new Set<DeepResearchRun['status']>([
  'completed',
  'completed_with_limitations',
  'cancelled',
  'failed',
]);

// research_completed/failed/cancelled -- see `ResearchEventType` in
// `app/ai/runtime/events/research/models.py`. `research_awaiting_approval`
// is handled separately -- it doesn't end the stream (see below).
const TERMINAL_EVENT_TYPES = new Set(['research_completed', 'research_failed', 'research_cancelled']);

const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY_MS = 1500;

function stageForRun(run: DeepResearchRun): DeepResearchStage {
  if (run.status === 'awaiting_approval') return 'report_review';
  if (run.status === 'cancelled' || run.status === 'failed') return 'failed';
  if (TERMINAL_RUN_STATUSES.has(run.status)) return 'done';
  return 'running';
}

function turnFromProposal(query: string, proposal: DeepResearchProposal): DeepResearchTurn {
  return {
    localId: crypto.randomUUID(),
    query,
    createdAt: proposal.created_at,
    proposal,
    run: null,
    stage: 'plan_review',
    events: [],
    draft: null,
    reportDownloadUrl: null,
    linearAnswer: null,
  };
}

/** Reconstructs a turn for a run that already exists server-side (conversation
 * replay after a refresh) -- unlike `turnFromProposal`, this starts from the
 * run's actual persisted status rather than assuming a fresh `plan_review`. */
function turnFromRun(proposal: DeepResearchProposal, run: DeepResearchRun): DeepResearchTurn {
  return {
    ...turnFromProposal(proposal.query, proposal),
    run,
    stage: stageForRun(run),
  };
}

function patchTurn(
  turns: DeepResearchTurn[],
  localId: string,
  patch: Partial<DeepResearchTurn> | ((t: DeepResearchTurn) => Partial<DeepResearchTurn>)
): DeepResearchTurn[] {
  return turns.map((t) =>
    t.localId === localId ? { ...t, ...(typeof patch === 'function' ? patch(t) : patch) } : t
  );
}

function errorMessage(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback;
}

/**
 * `onConversationLearned` threads a `conversation_id` a Deep Research call
 * reveals back up to the shared conversation state in `page.tsx` -- without
 * it, Deep Research turns always start (and stay in) their own conversation,
 * separate from any Linear Research turns in the same session (see
 * `ResearchConversation`'s FK from `ResearchRun`/`ResearchProposal`/
 * `ResearchSession`, which already supports mixing both turn types; the gap
 * was purely that the frontend never learned/reused the id). A brand new
 * Deep Research conversation's id isn't known until the run actually
 * publishes (`ResearchService.publish_runtime_report` is the only place a
 * `ResearchConversation` row gets created for a fresh thread) -- so this
 * fires mainly from `finalizeRun`, not from `createProposal`/`approve`.
 */
export function useDeepResearch(onConversationLearned?: (conversationId: string) => void) {
  const [turns, setTurns] = useState<DeepResearchTurn[]>([]);
  const activeStreams = useRef<Record<string, AbortController>>({});

  const learnConversationId = useCallback(
    (conversationId: string | null) => {
      if (conversationId) onConversationLearned?.(conversationId);
    },
    [onConversationLearned]
  );

  const stopStream = useCallback((localId: string) => {
    const controller = activeStreams.current[localId];
    if (controller) {
      controller.abort();
      delete activeStreams.current[localId];
    }
  }, []);

  useEffect(
    () => () => {
      Object.values(activeStreams.current).forEach((c) => c.abort());
    },
    []
  );

  const fetchReportDownload = useCallback(async (localId: string, runId: string) => {
    try {
      const download = await api.research.getReportDownload(runId);
      setTurns((prev) => patchTurn(prev, localId, { reportDownloadUrl: download.download_url }));
    } catch {
      // Best-effort: the completed-run card still renders correctly without
      // a download link -- the user can still see the report status.
    }
  }, []);

  /** Fetches the draft awaiting review once a run pauses at the
   * report-approval interrupt -- the only point it's readable at all (see
   * `ResearchDraftInspectionService`, which reads it straight out of the
   * paused run's LangGraph checkpoint). */
  const fetchDraft = useCallback(async (localId: string, runId: string) => {
    try {
      const draft = await api.research.getDraft(runId);
      setTurns((prev) => patchTurn(prev, localId, { draft }));
    } catch {
      // Best-effort -- the review card still renders the approve/reject
      // buttons without the draft preview if this fetch fails.
    }
  }, []);

  /** A rejected report never gets a PDF (`persist_final_report` was
   * skipped) -- fetch the plain-text answer/citations the run still
   * published instead, via the same session-replay endpoint Linear
   * Research turns use. */
  const fetchLinearAnswer = useCallback(async (localId: string, researchId: string) => {
    try {
      const session = await api.research.get(researchId);
      setTurns((prev) =>
        patchTurn(prev, localId, {
          linearAnswer: { answer: session.answer, citations: session.citations },
        })
      );
    } catch {
      // Best-effort, mirrors `fetchReportDownload` -- the completed-run
      // card still renders correctly (just without the answer text) if
      // this fetch fails.
    }
  }, []);

  /** Authoritative final state once the live event stream reports a terminal event -- the
   * stream's own labels never carry `status` (only safe milestone text), so this is the
   * one point where we still fetch `GET /research/runs/{id}` directly. */
  const finalizeRun = useCallback(
    async (localId: string, runId: string) => {
      try {
        const run = await api.research.getRun(runId);
        setTurns((prev) => patchTurn(prev, localId, { run, stage: stageForRun(run) }));
        learnConversationId(run.conversation_id);
        if (run.status === 'completed' || run.status === 'completed_with_limitations') {
          if (run.terminal_reason === 'report_rejected_returned_as_answer' && run.research_id) {
            void fetchLinearAnswer(localId, run.research_id);
          } else {
            void fetchReportDownload(localId, runId);
          }
        }
      } catch (err) {
        setTurns((prev) =>
          patchTurn(prev, localId, {
            stage: 'error',
            error: errorMessage(err, 'Could not confirm the final research run status.'),
          })
        );
      }
    },
    [fetchReportDownload, fetchLinearAnswer, learnConversationId]
  );

  /**
   * Consumes the live progress-event SSE stream for one run, from
   * `approve()` all the way through the report-approval pause/resume to a
   * terminal event -- one connection for the whole lifecycle, since the
   * server-side replay loop does not close on `research_awaiting_approval`
   * (see `GET /research/runs/{id}/events` in `app/api/v1/research.py`).
   * Reconnects (resuming from the last seen cursor) on a dropped
   * connection, up to `MAX_RECONNECT_ATTEMPTS`.
   */
  const streamRun = useCallback(
    (localId: string, runId: string) => {
      stopStream(localId);
      const controller = new AbortController();
      activeStreams.current[localId] = controller;

      void (async () => {
        let cursor = 0;
        let attempt = 0;

        while (!controller.signal.aborted) {
          try {
            for await (const { data: event } of api.research.streamRunEvents(
              runId,
              cursor,
              controller.signal
            )) {
              attempt = 0;
              const rawCursor = event.metadata?.cursor;
              if (typeof rawCursor === 'number') cursor = rawCursor;
              const label = (event.metadata?.label as string | undefined) ?? event.type;

              setTurns((prev) =>
                patchTurn(prev, localId, (t) => ({
                  events: [...t.events, { type: event.type, label, timestamp: event.timestamp }],
                }))
              );

              if (event.type === 'research_awaiting_approval') {
                setTurns((prev) => patchTurn(prev, localId, { stage: 'report_review' }));
                void fetchDraft(localId, runId);
              }

              if (TERMINAL_EVENT_TYPES.has(event.type)) {
                delete activeStreams.current[localId];
                await finalizeRun(localId, runId);
                return;
              }
            }
            // Generator ended without a terminal event (server-side duration
            // ceiling, or the connection just dropped) -- reconnect from `cursor`.
          } catch {
            if (controller.signal.aborted) return;
          }

          attempt += 1;
          if (attempt > MAX_RECONNECT_ATTEMPTS) {
            setTurns((prev) =>
              patchTurn(prev, localId, {
                stage: 'error',
                error: 'Lost the live connection to this research run.',
              })
            );
            return;
          }
          await new Promise((resolve) => setTimeout(resolve, RECONNECT_DELAY_MS));
        }
      })();
    },
    [stopStream, finalizeRun, fetchDraft]
  );

  /** Manual "Deep Research" mode submission -- creates and shows a fresh proposal. */
  const createProposal = useCallback(
    async (query: string, options: DeepResearchAskOptions = {}): Promise<string | null> => {
      try {
        const proposal = await api.research.createProposal(query, options);
        const turn = turnFromProposal(query, proposal);
        setTurns((prev) => [...prev, turn]);
        learnConversationId(proposal.conversation_id);
        return turn.localId;
      } catch {
        return null;
      }
    },
    [learnConversationId]
  );

  /** Escalation-suggestion acceptance -- reuses the proposal the check already persisted, no second planner call. */
  const startFromProposal = useCallback(
    (query: string, proposal: DeepResearchProposal): string => {
      const turn = turnFromProposal(query, proposal);
      setTurns((prev) => [...prev, turn]);
      learnConversationId(proposal.conversation_id);
      return turn.localId;
    },
    [learnConversationId]
  );

  const approve = useCallback(
    async (localId: string, proposalId: string) => {
      try {
        const run = await api.research.approveProposal(proposalId);
        setTurns((prev) => patchTurn(prev, localId, { run, stage: stageForRun(run) }));
        learnConversationId(run.conversation_id);
        streamRun(localId, run.research_run_id);
      } catch (err) {
        setTurns((prev) =>
          patchTurn(prev, localId, {
            stage: 'error',
            error: errorMessage(err, 'Could not approve this proposal.'),
          })
        );
      }
    },
    [streamRun, learnConversationId]
  );

  const submitReportDecision = useCallback(
    async (
      localId: string,
      runId: string,
      approved: boolean,
      reason?: string,
      editedDraft?: DeepResearchDraftEdit
    ) => {
      try {
        const run = await api.research.submitReportDecision(runId, approved, reason, editedDraft);
        // Optimistic: the run itself is still `awaiting_approval` at this
        // point (the worker hasn't resumed the graph yet) -- flip to
        // `running` immediately so the approve/reject buttons disappear
        // right away, rather than waiting for the next stream event. The
        // still-open event stream from `approve()` carries the rest.
        setTurns((prev) => patchTurn(prev, localId, { run, stage: 'running' }));
        learnConversationId(run.conversation_id);
      } catch (err) {
        setTurns((prev) =>
          patchTurn(prev, localId, {
            stage: 'error',
            error: errorMessage(err, 'Could not submit your report decision.'),
          })
        );
      }
    },
    [learnConversationId]
  );

  const cancel = useCallback(async (localId: string, runId: string) => {
    try {
      const run = await api.research.cancelRun(runId);
      setTurns((prev) => patchTurn(prev, localId, { run }));
      // Cancellation is cooperative, not synchronous -- leave the event
      // stream running so the UI reflects whatever the run actually does
      // next (a few more events may land before it honors the request),
      // finalizing normally once `research_cancelled` arrives.
    } catch (err) {
      setTurns((prev) =>
        patchTurn(prev, localId, {
          stage: 'error',
          error: errorMessage(err, 'Could not cancel this research run.'),
        })
      );
    }
  }, []);

  /**
   * Reconstructs every Deep Research turn in a conversation thread -- the
   * counterpart to `useResearch()`'s `selectConversation`, called alongside
   * it so a page refresh (or switching to a past conversation) restores
   * both turn types instead of only Linear Research ones. For any run
   * that isn't terminal yet, resumes its live event stream from cursor 0,
   * which replays the full persisted history before following live (see
   * `GET /research/runs/{id}/events`'s replay loop) -- so the step log
   * comes back too, not just the current stage.
   */
  const hydrateFromConversation = useCallback(
    async (conversationId: string) => {
      try {
        const conversation = await api.research.getConversation(conversationId);
        const hydrated = conversation.deep_research_runs.map(({ proposal, run }) =>
          turnFromRun(proposal, run)
        );
        setTurns(hydrated);
        for (const turn of hydrated) {
          if (!turn.run) continue;
          if (TERMINAL_RUN_STATUSES.has(turn.run.status)) {
            if (turn.run.status === 'completed' || turn.run.status === 'completed_with_limitations') {
              if (turn.run.terminal_reason === 'report_rejected_returned_as_answer' && turn.run.research_id) {
                void fetchLinearAnswer(turn.localId, turn.run.research_id);
              } else {
                void fetchReportDownload(turn.localId, turn.run.research_run_id);
              }
            }
          } else {
            streamRun(turn.localId, turn.run.research_run_id);
          }
        }
      } catch {
        // Best-effort, mirrors `selectConversation` -- a failed hydration
        // just leaves Deep Research turns empty rather than blocking the
        // rest of the conversation from loading.
      }
    },
    [fetchReportDownload, fetchLinearAnswer, streamRun]
  );

  const dismiss = useCallback(
    (localId: string) => {
      stopStream(localId);
      setTurns((prev) => prev.filter((t) => t.localId !== localId));
    },
    [stopStream]
  );

  const reset = useCallback(() => {
    Object.values(activeStreams.current).forEach((c) => c.abort());
    activeStreams.current = {};
    setTurns([]);
  }, []);

  return {
    turns,
    createProposal,
    startFromProposal,
    approve,
    submitReportDecision,
    hydrateFromConversation,
    reset,
    cancel,
    dismiss,
  };
}
