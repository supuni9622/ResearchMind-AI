'use client';

import { SparklesIcon } from '@/components/ui/icons';
import type { ResearchEscalationCheck } from '@/features/research/types';

export function EscalationSuggestion({
  check,
  onAccept,
  onReject,
  loading,
}: {
  check: ResearchEscalationCheck;
  onAccept: () => void;
  onReject: () => void;
  loading: boolean;
}) {
  if (!check.proposal) return null;
  const taskCount = check.proposal.plan.tasks.length;

  return (
    <div className="max-w-2xl mb-4 border border-sage-700/50 rounded-xl bg-sage-500/5 px-5 py-4">
      <div className="flex items-start gap-3">
        <span className="text-sage-500 flex-shrink-0 mt-0.5">
          <SparklesIcon size={15} />
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-stone-100 text-sm leading-snug mb-1">
            This looks like it&apos;d work better as a comprehensive research report.
          </p>
          <p className="text-stone-500 text-[13px] leading-snug mb-3">{check.reason}</p>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={loading}
              onClick={onAccept}
              className="px-3 py-1.5 rounded-lg bg-sage-600 hover:bg-sage-500 disabled:bg-ink-700 disabled:text-stone-700 text-stone-100 text-[12px] font-medium transition-colors duration-150"
            >
              Run Deep Research ({taskCount} task{taskCount === 1 ? '' : 's'})
            </button>
            <button
              type="button"
              disabled={loading}
              onClick={onReject}
              className="px-3 py-1.5 rounded-lg border border-ink-600 hover:border-ink-500 text-stone-400 text-[12px] transition-colors duration-150"
            >
              No, keep it quick
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
