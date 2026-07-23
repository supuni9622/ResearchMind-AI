'use client';

import { useState } from 'react';
import type { DeepResearchTurn } from '@/features/research/types';
import { AlertIcon, ArrowDownIcon, CheckCircleIcon, TargetIcon } from '@/components/ui/icons';

// Mirrors `ResearchPlanningPolicy._BUDGETS`
// (apps/api/app/ai/runtime/research/planner/policies.py) -- informational
// only; the backend budget enforcement is the actual source of truth.
const BUDGET_HINT: Record<string, { costUsd: number; seconds: number }> = {
  simple: { costUsd: 0.5, seconds: 120 },
  moderate: { costUsd: 2, seconds: 300 },
  complex: { costUsd: 5, seconds: 600 },
};

const STATUS_LABEL: Record<string, string> = {
  created: 'Queued',
  planning: 'Planning',
  researching: 'Researching',
  reviewing: 'Reviewing',
  synthesizing: 'Writing report',
  paused: 'Paused',
  awaiting_approval: 'Awaiting your review',
  completed: 'Completed',
  completed_with_limitations: 'Completed (with limitations)',
  cancelled: 'Cancelled',
  failed: 'Failed',
};

function ComplexityBadge({ complexity }: { complexity: string }) {
  const budget = BUDGET_HINT[complexity];
  return (
    <span className="inline-flex items-center gap-1 font-mono text-[10px] uppercase tracking-widest text-amber-500 border border-amber-800/40 bg-amber-500/5 rounded px-1.5 py-0.5">
      {complexity}
      {budget && (
        <span className="text-stone-600 normal-case tracking-normal">
          · up to ${budget.costUsd.toFixed(2)}, ~{Math.round(budget.seconds / 60)}min
        </span>
      )}
    </span>
  );
}

export function DeepResearchBlock({
  turn,
  focused,
  onFocus,
  onApprove,
  onCancel,
  onReportDecision,
}: {
  turn: DeepResearchTurn;
  focused: boolean;
  onFocus: () => void;
  onApprove: () => void;
  onCancel: () => void;
  onReportDecision: (approved: boolean, reason?: string) => void;
}) {
  const [rejectReason, setRejectReason] = useState('');
  const [showRejectInput, setShowRejectInput] = useState(false);
  const { plan } = turn.proposal;
  const goal = plan.rewritten_goal ?? plan.goal;

  return (
    <div
      onClick={onFocus}
      className={`border rounded-xl overflow-hidden transition-colors duration-150 cursor-pointer ${
        focused ? 'border-sage-700/60' : 'border-ink-600 hover:border-ink-500'
      }`}
    >
      <div className="px-5 py-4 border-b border-ink-700 bg-ink-800/40">
        <div className="flex items-center justify-between mb-1.5">
          <p className="font-mono text-stone-600 text-[10px] tracking-[0.2em] uppercase">
            Deep Research
          </p>
          <ComplexityBadge complexity={plan.complexity} />
        </div>
        <p className="text-stone-100 text-[15px] leading-snug">{turn.query}</p>
      </div>

      <div className="px-5 py-4">
        {turn.stage === 'error' && (
          <div className="flex items-start gap-2.5 px-4 py-3 rounded-lg border border-red-800/50 bg-red-900/20 text-red-400 text-[13px]">
            <AlertIcon size={13} className="flex-shrink-0 mt-0.5" />
            <span>{turn.error}</span>
          </div>
        )}

        {turn.stage === 'plan_review' && (
          <div>
            <p className="text-stone-300 text-[13px] leading-relaxed mb-3">{goal}</p>
            <ul className="space-y-1.5 mb-4">
              {plan.tasks.map((task) => (
                <li
                  key={task.task_id}
                  className="flex items-start gap-2 text-[13px] text-stone-400"
                >
                  <TargetIcon size={11} className="flex-shrink-0 mt-0.5 text-stone-600" />
                  <span>{task.question}</span>
                </li>
              ))}
            </ul>
            {plan.limitations.length > 0 && (
              <ul className="mb-4 space-y-1">
                {plan.limitations.map((limitation, i) => (
                  <li key={i} className="text-[12px] text-stone-600">
                    · {limitation}
                  </li>
                ))}
              </ul>
            )}
            <div className="flex items-center gap-2 pt-3 border-t border-ink-700">
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onApprove();
                }}
                className="px-3 py-1.5 rounded-lg bg-sage-600 hover:bg-sage-500 text-stone-100 text-[12px] font-medium transition-colors duration-150"
              >
                Approve &amp; run
              </button>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onCancel();
                }}
                className="px-3 py-1.5 rounded-lg border border-ink-600 hover:border-ink-500 text-stone-400 text-[12px] transition-colors duration-150"
              >
                Dismiss
              </button>
            </div>
          </div>
        )}

        {turn.stage === 'running' && (
          <div>
            <div className="space-y-1.5">
              {turn.events.length === 0 ? (
                <div className="flex items-center gap-2.5">
                  <span className="w-3 h-3 flex-shrink-0 flex items-center justify-center">
                    <span className="w-1.5 h-1.5 rounded-full bg-sage-500 animate-pulse" />
                  </span>
                  <span className="text-stone-200 text-[13px]">Starting…</span>
                </div>
              ) : (
                turn.events.map((event, i) => {
                  const isLatest = i === turn.events.length - 1;
                  return (
                    <div key={i} className="flex items-center gap-2.5">
                      {isLatest ? (
                        <span className="w-3 h-3 flex-shrink-0 flex items-center justify-center">
                          <span className="w-1.5 h-1.5 rounded-full bg-sage-500 animate-pulse" />
                        </span>
                      ) : (
                        <span className="text-sage-700 flex-shrink-0">
                          <CheckCircleIcon size={12} />
                        </span>
                      )}
                      <span
                        className={`text-[13px] ${isLatest ? 'text-stone-200' : 'text-stone-600'}`}
                      >
                        {event.label}
                      </span>
                    </div>
                  );
                })
              )}
            </div>
            {turn.run && (
              <div className="flex justify-end pt-2">
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onCancel();
                  }}
                  className="font-mono text-[10px] text-stone-600 hover:text-red-400 transition-colors"
                >
                  cancel
                </button>
              </div>
            )}
          </div>
        )}

        {turn.stage === 'report_review' && (
          <div>
            <div className="flex items-center gap-2.5 mb-3">
              <span className="text-sage-500 flex-shrink-0">
                <CheckCircleIcon size={13} />
              </span>
              <span className="text-stone-200 text-[13px]">
                Your report is ready for review before it&apos;s published.
              </span>
            </div>
            {showRejectInput ? (
              <div onClick={(e) => e.stopPropagation()}>
                <textarea
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="What's wrong with it? (optional)"
                  rows={2}
                  className="w-full bg-ink-800 border border-ink-500 rounded-lg px-3 py-2 text-stone-100 text-[13px] placeholder-stone-600 resize-none focus:outline-none focus:border-sage-600 mb-2"
                />
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => onReportDecision(false, rejectReason || undefined)}
                    className="px-3 py-1.5 rounded-lg bg-red-900/40 hover:bg-red-900/60 text-red-300 text-[12px] transition-colors duration-150"
                  >
                    Confirm reject
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowRejectInput(false)}
                    className="px-3 py-1.5 rounded-lg border border-ink-600 hover:border-ink-500 text-stone-400 text-[12px] transition-colors duration-150"
                  >
                    Back
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onReportDecision(true);
                  }}
                  className="px-3 py-1.5 rounded-lg bg-sage-600 hover:bg-sage-500 text-stone-100 text-[12px] font-medium transition-colors duration-150"
                >
                  Approve report
                </button>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowRejectInput(true);
                  }}
                  className="px-3 py-1.5 rounded-lg border border-ink-600 hover:border-ink-500 text-stone-400 text-[12px] transition-colors duration-150"
                >
                  Reject
                </button>
              </div>
            )}
          </div>
        )}

        {turn.stage === 'done' && (
          <div className="flex items-center justify-between pt-1">
            <span className="flex items-center gap-1.5 text-stone-500 text-[13px]">
              <CheckCircleIcon size={13} className="text-sage-500" />
              {turn.run ? (STATUS_LABEL[turn.run.status] ?? turn.run.status) : 'Completed'}
            </span>
            {turn.reportDownloadUrl ? (
              <a
                href={turn.reportDownloadUrl}
                target="_blank"
                rel="noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="flex items-center gap-1.5 font-mono text-[11px] text-sage-500 hover:text-sage-400 transition-colors"
              >
                <ArrowDownIcon size={11} />
                Download PDF
              </a>
            ) : (
              <span className="font-mono text-[10px] text-stone-700">Preparing PDF…</span>
            )}
          </div>
        )}

        {turn.stage === 'failed' && (
          <div className="flex items-center gap-2.5 px-4 py-3 rounded-lg border border-red-800/50 bg-red-900/20 text-red-400 text-[13px]">
            <AlertIcon size={13} className="flex-shrink-0" />
            <span>This run {turn.run?.status === 'cancelled' ? 'was cancelled' : 'failed'}.</span>
          </div>
        )}
      </div>
    </div>
  );
}
