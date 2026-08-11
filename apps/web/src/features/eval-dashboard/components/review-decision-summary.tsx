import { Badge } from '@/components/ui/badge';

const DECISION_TONE: Record<string, 'sage' | 'amber' | 'red' | 'neutral'> = {
  pass: 'sage',
  finalize_with_limitations: 'amber',
  revise_synthesis: 'amber',
  research_gaps: 'amber',
  fail: 'red',
};

export function ReviewDecisionSummary({ counts }: { counts: Record<string, number> }) {
  const entries = Object.entries(counts);

  if (entries.length === 0) {
    return (
      <p className="text-stone-600 text-[12px]">
        No Deep Research runs with a review decision yet for this owner.
      </p>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      {entries
        .sort(([, a], [, b]) => b - a)
        .map(([decision, count]) => (
          <Badge key={decision} tone={DECISION_TONE[decision] ?? 'neutral'}>
            {decision.replace(/_/g, ' ')} · {count}
          </Badge>
        ))}
    </div>
  );
}
