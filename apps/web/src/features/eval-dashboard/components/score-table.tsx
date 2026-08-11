import type { EvalScore } from '@/lib/api';
import { Badge } from '@/components/ui/badge';

const SOURCE_LABEL: Record<string, string> = {
  online_sampled: 'Online',
  human_feedback: 'Feedback',
  offline_benchmark: 'Offline',
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

function ScoreCell({ score }: { score: number | null }) {
  if (score === null) return <span className="text-stone-600">—</span>;
  return <span className="font-mono">{score.toFixed(2)}</span>;
}

export function ScoreTable({ scores }: { scores: EvalScore[] }) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center px-3 pb-2 border-b border-ink-700 mb-1">
        <span className="font-mono text-stone-600 text-[10px] tracking-widest uppercase flex-1">
          Metric
        </span>
        <span className="font-mono text-stone-600 text-[10px] tracking-widest uppercase w-16 text-right">
          Score
        </span>
        <span className="font-mono text-stone-600 text-[10px] tracking-widest uppercase w-20 text-right">
          Passed
        </span>
        <span className="font-mono text-stone-600 text-[10px] tracking-widest uppercase w-20 text-right hidden sm:inline">
          Source
        </span>
        <span className="font-mono text-stone-600 text-[10px] tracking-widest uppercase w-32 text-right hidden md:inline">
          When
        </span>
      </div>

      {scores.map((score) => (
        <div
          key={score.id}
          className="flex items-center px-3 py-2.5 rounded-lg border border-ink-700 hover:border-ink-500 transition-colors duration-100"
          title={score.reason ?? undefined}
        >
          <div className="flex-1 min-w-0">
            <p className="text-stone-200 text-[13px] truncate">{score.metric_name}</p>
            {score.reason && (
              <p className="text-stone-600 text-[11px] truncate">{score.reason}</p>
            )}
          </div>
          <span className="w-16 text-right text-stone-300 text-[13px]">
            <ScoreCell score={score.score} />
          </span>
          <span className="w-20 text-right">
            {score.passed === null ? (
              <span className="text-stone-600 text-[12px]">—</span>
            ) : (
              <Badge tone={score.passed ? 'sage' : 'red'}>{score.passed ? 'pass' : 'fail'}</Badge>
            )}
          </span>
          <span className="w-20 text-right hidden sm:inline">
            <Badge tone="neutral">{SOURCE_LABEL[score.source] ?? score.source}</Badge>
          </span>
          <span className="font-mono text-stone-600 text-[11px] w-32 text-right hidden md:inline">
            {formatDate(score.created_at)}
          </span>
        </div>
      ))}
    </div>
  );
}
