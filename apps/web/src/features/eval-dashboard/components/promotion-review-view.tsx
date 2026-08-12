'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  api,
  type ConfirmPromotionPayload,
  type PromotionCandidate,
  type PromotionCandidateView,
  type PromotionDifficulty,
  type PromotionDirection,
  type PromotionFailureCategory,
  type PromotionQueryType,
  type PromotionWorkflow,
} from '@/lib/api';
import { Pill } from '@/components/ui/badge';
import { EmptyState } from '@/components/ui/empty-state';

const QUERY_TYPES: PromotionQueryType[] = [
  'factual',
  'synthesis',
  'comparison',
  'exploratory',
  'unanswerable',
];
const DIFFICULTIES: PromotionDifficulty[] = ['easy', 'medium', 'hard'];
const WORKFLOWS: PromotionWorkflow[] = ['chat', 'linear_research', 'deep_research'];
const FAILURE_CATEGORIES: PromotionFailureCategory[] = [
  'wrong_citation',
  'hallucination',
  'retrieval_miss',
  'unnecessary_tool_use',
  'abstention_failure',
  'workflow_loop',
  'schema_violation',
  'injection_success',
];

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

function TraceLink({ generationId }: { generationId: string }) {
  const [state, setState] = useState<'idle' | 'loading' | 'none'>('idle');

  async function open() {
    setState('loading');
    try {
      const { trace_url } = await api.promotionReview.traceUrl(generationId);
      if (trace_url) {
        window.open(trace_url, '_blank', 'noopener,noreferrer');
        setState('idle');
      } else {
        setState('none');
      }
    } catch {
      setState('none');
    }
  }

  if (state === 'none') {
    return <span className="text-stone-700 text-[11px]">no trace available</span>;
  }

  return (
    <button
      type="button"
      onClick={open}
      disabled={state === 'loading'}
      className="text-amber-400 text-[11px] hover:underline disabled:opacity-50"
    >
      {state === 'loading' ? 'looking up…' : 'View trace in LangSmith ↗'}
    </button>
  );
}

function ConfirmForm({
  candidate,
  direction,
  onDone,
}: {
  candidate: PromotionCandidate;
  direction: PromotionDirection;
  onDone: () => void;
}) {
  const [question, setQuestion] = useState('');
  const [referenceAnswer, setReferenceAnswer] = useState('');
  const [contexts, setContexts] = useState('');
  const [referenceContextIds, setReferenceContextIds] = useState('');
  const [expectedCitationIds, setExpectedCitationIds] = useState('');
  const [queryType, setQueryType] = useState<PromotionQueryType>('factual');
  const [difficulty, setDifficulty] = useState<PromotionDifficulty>('medium');
  const [workflow, setWorkflow] = useState<PromotionWorkflow>('chat');
  const [rubric, setRubric] = useState('');
  const [failureCategory, setFailureCategory] = useState<PromotionFailureCategory>(
    'wrong_citation'
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setSubmitting(true);
    setError(null);
    try {
      const payload: ConfirmPromotionPayload = {
        source: candidate.source,
        direction,
        owner_id: candidate.owner_id,
        generation_id: candidate.generation_id,
        question,
        reference_answer: referenceAnswer,
        contexts: contexts
          .split('\n')
          .map((line) => line.trim())
          .filter(Boolean),
        reference_context_ids: referenceContextIds
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
        expected_citation_ids: expectedCitationIds
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
        query_type: queryType,
        difficulty,
        workflow,
        rubric: rubric || null,
        failure_category: direction === 'failure' ? failureCategory : null,
      };
      await api.promotionReview.confirm(payload);
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to confirm promotion.');
    } finally {
      setSubmitting(false);
    }
  }

  const inputClass =
    'w-full px-3 py-2 rounded-lg bg-ink-800 border border-ink-600 text-stone-200 text-[13px] placeholder:text-stone-600 focus:outline-none focus:border-sage-600';

  return (
    <div className="mt-3 p-4 rounded-lg border border-ink-600 bg-ink-800/40 space-y-3">
      <p className="text-stone-500 text-[11px]">
        Fill this in from what you read in the LangSmith trace above — this app never stores the
        original content itself.
      </p>
      <textarea
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="Question"
        rows={2}
        className={inputClass}
      />
      <textarea
        value={referenceAnswer}
        onChange={(e) => setReferenceAnswer(e.target.value)}
        placeholder="Reference answer"
        rows={3}
        className={inputClass}
      />
      <textarea
        value={contexts}
        onChange={(e) => setContexts(e.target.value)}
        placeholder="Context passages, one per line"
        rows={3}
        className={inputClass}
      />
      <div className="grid grid-cols-2 gap-3">
        <input
          value={referenceContextIds}
          onChange={(e) => setReferenceContextIds(e.target.value)}
          placeholder="reference_context_ids (comma-separated)"
          className={inputClass}
        />
        <input
          value={expectedCitationIds}
          onChange={(e) => setExpectedCitationIds(e.target.value)}
          placeholder="expected_citation_ids (comma-separated)"
          className={inputClass}
        />
      </div>
      <div className="grid grid-cols-3 gap-3">
        <select
          value={queryType}
          onChange={(e) => setQueryType(e.target.value as PromotionQueryType)}
          className={inputClass}
        >
          {QUERY_TYPES.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
        <select
          value={difficulty}
          onChange={(e) => setDifficulty(e.target.value as PromotionDifficulty)}
          className={inputClass}
        >
          {DIFFICULTIES.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
        <select
          value={workflow}
          onChange={(e) => setWorkflow(e.target.value as PromotionWorkflow)}
          className={inputClass}
        >
          {WORKFLOWS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </div>
      {direction === 'failure' && (
        <select
          value={failureCategory}
          onChange={(e) => setFailureCategory(e.target.value as PromotionFailureCategory)}
          className={inputClass}
        >
          {FAILURE_CATEGORIES.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      )}
      <input
        value={rubric}
        onChange={(e) => setRubric(e.target.value)}
        placeholder="Rubric (optional)"
        className={inputClass}
      />

      {error && <p className="text-red-400 text-[12px]">{error}</p>}

      <div className="flex justify-end gap-2">
        <button
          type="button"
          onClick={onDone}
          className="px-3 py-1.5 rounded-lg border border-ink-600 text-stone-400 text-[13px] hover:border-ink-400"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={submit}
          disabled={submitting || !question || !referenceAnswer || !contexts}
          className="px-3 py-1.5 rounded-lg bg-sage-700 text-white text-[13px] hover:bg-sage-600 disabled:opacity-40"
        >
          {submitting
            ? 'Promoting…'
            : direction === 'good'
              ? 'Confirm → rag_answer_gold'
              : 'Confirm → production_failures'}
        </button>
      </div>
    </div>
  );
}

function CandidateRow({
  candidate,
  direction,
  onResolved,
}: {
  candidate: PromotionCandidate;
  direction: PromotionDirection;
  onResolved: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [rejecting, setRejecting] = useState(false);

  async function reject() {
    setRejecting(true);
    try {
      await api.promotionReview.reject({
        source: candidate.source,
        owner_id: candidate.owner_id,
        generation_id: candidate.generation_id,
      });
      onResolved();
    } finally {
      setRejecting(false);
    }
  }

  return (
    <div className="p-3 rounded-lg border border-ink-700">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-stone-200 text-[13px] truncate">{candidate.reason}</p>
          <p className="font-mono text-stone-600 text-[10px] mt-0.5">
            {candidate.source} · owner {candidate.owner_id.slice(0, 8)} · generation{' '}
            {candidate.generation_id.slice(0, 8)} · {formatDate(candidate.created_at)}
          </p>
          <div className="mt-1.5">
            <TraceLink generationId={candidate.generation_id} />
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <button
            type="button"
            onClick={reject}
            disabled={rejecting}
            className="px-3 py-1.5 rounded-lg border border-ink-600 text-stone-400 text-[12px] hover:border-red-700 hover:text-red-400 disabled:opacity-40"
          >
            Reject
          </button>
          <button
            type="button"
            onClick={() => setExpanded((value) => !value)}
            className="px-3 py-1.5 rounded-lg border border-ink-600 text-stone-200 text-[12px] hover:border-sage-600"
          >
            {expanded ? 'Close' : 'Review'}
          </button>
        </div>
      </div>
      {expanded && (
        <ConfirmForm candidate={candidate} direction={direction} onDone={onResolved} />
      )}
    </div>
  );
}

export function PromotionReviewView({ onForbidden }: { onForbidden: () => void }) {
  const [view, setView] = useState<PromotionCandidateView>('failure');
  const [candidates, setCandidates] = useState<PromotionCandidate[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.promotionReview.listCandidates({ direction: view, limit: 25 });
      setCandidates(res.items);
      setTotal(res.total);
    } catch (err) {
      if (err instanceof Error && (err as Error & { status?: number }).status === 403) {
        onForbidden();
      }
    } finally {
      setLoading(false);
    }
  }, [view, onForbidden]);

  useEffect(() => {
    load();
  }, [load]);

  // 'preference' is a separate list, not a separate dataset -- overriding
  // one still confirms with direction='failure', same target as the
  // failure queue itself.
  const confirmDirection: PromotionDirection = view === 'good' ? 'good' : 'failure';

  return (
    <div>
      <p className="text-stone-600 text-[12px] mb-5">
        E10&apos;s promotion loop — confirmed failures feed <code>production_failures.json</code>,
        confirmed good examples feed <code>rag_answer_gold.json</code> directly. Neither file is
        touched here: confirming just records the decision, and{' '}
        <code>sync_promoted_examples.py</code> appends it as a separate, git-reviewable step.
      </p>

      <div className="flex items-center gap-2 mb-5">
        <Pill active={view === 'failure'} onClick={() => setView('failure')}>
          Failure candidates
        </Pill>
        <Pill active={view === 'good'} onClick={() => setView('good')}>
          Good candidates
        </Pill>
        <Pill active={view === 'preference'} onClick={() => setView('preference')}>
          Preference (override)
        </Pill>
        <span className="text-stone-600 text-[11px] ml-2">{total} pending</span>
      </div>

      {view === 'preference' && (
        <p className="text-stone-600 text-[12px] mb-4">
          Thumbs-down feedback E11&apos;s classifier called a subjective preference rather than an
          objective defect — kept out of Failure candidates by default, since a misclassified
          objective complaint could otherwise contaminate the shared dataset. If you read the
          trace and disagree with the classifier, confirm it here to promote it into{' '}
          <code>production_failures.json</code> anyway.
        </p>
      )}

      {loading ? (
        <p className="text-stone-600 text-[13px] py-8">Loading…</p>
      ) : candidates.length === 0 ? (
        <EmptyState
          title="Nothing to review"
          description={
            view === 'failure'
              ? 'No unreviewed thumbs-down (classified objective) or failed online-sampled checks right now.'
              : view === 'good'
                ? 'No unreviewed thumbs-up feedback right now.'
                : "No unreviewed thumbs-down classified 'preference' right now."
          }
        />
      ) : (
        <div className="space-y-2">
          {candidates.map((candidate) => (
            <CandidateRow
              key={`${candidate.source}-${candidate.generation_id}`}
              candidate={candidate}
              direction={confirmDirection}
              onResolved={load}
            />
          ))}
        </div>
      )}
    </div>
  );
}
