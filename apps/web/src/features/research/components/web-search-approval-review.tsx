'use client';

import type { DeepResearchPendingWebSearch } from '@/features/research/types';

const labelClass = 'font-mono text-stone-600 text-[10px] tracking-[0.15em] uppercase mb-1 block';

/**
 * Read-only preview of the agent's own web-search suggestion, awaiting
 * approval -- reached only in AUTO mode without pre-approval, when the
 * agent decided the private evidence gathered so far isn't enough. Nothing
 * here is editable: unlike a plan or report, there's nothing to revise --
 * just approve (search) or reject (continue with the existing document-only
 * evidence, exactly as if this feature didn't exist).
 */
export function WebSearchApprovalReview({
  suggestion,
}: {
  suggestion: DeepResearchPendingWebSearch;
}) {
  return (
    <div
      onClick={(e) => e.stopPropagation()}
      className="mb-4 rounded-lg border border-ink-700 bg-ink-800/30 p-4 space-y-3"
    >
      <div>
        <label className={labelClass}>Suggested web search</label>
        <p className="text-stone-100 text-[14px] leading-snug">&ldquo;{suggestion.suggested_query}&rdquo;</p>
      </div>
      <div>
        <label className={labelClass}>Why</label>
        <p className="text-stone-400 text-[13px] leading-relaxed">{suggestion.reason}</p>
      </div>
    </div>
  );
}
