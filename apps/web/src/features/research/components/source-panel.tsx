import type { ResearchTurn } from '@/features/research/types';
import { SectionLabel } from '@/components/ui/page-header';
import { CitationCard } from '@/features/research/components/citation-card';
import { SourceCard } from '@/features/research/components/source-card';
import { NetworkIcon, ClockIcon, LayersIcon } from '@/components/ui/icons';

function MetricTile({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="border border-ink-600 rounded-lg px-3 py-2.5">
      <div className="flex items-center gap-1.5 text-stone-600 mb-1.5">
        {icon}
        <span className="font-mono text-[9.5px] tracking-widest uppercase">{label}</span>
      </div>
      <p className="text-stone-200 text-[13px] font-medium tabular-nums">{value}</p>
    </div>
  );
}

export function SourcePanel({ turn }: { turn: ResearchTurn | null }) {
  const done = turn?.stage === 'done';

  return (
    <aside className="w-80 flex-shrink-0 border-l border-ink-600 bg-ink-900/50 h-full overflow-y-auto scrollbar-thin">
      <div className="px-5 py-4 border-b border-ink-700">
        <SectionLabel count={turn?.citations.length ?? 0}>Citations</SectionLabel>
      </div>

      <div className="px-4 py-4">
        {turn && turn.citations.length > 0 ? (
          <div className="space-y-2.5">
            {turn.citations.map((c) => (
              <CitationCard key={c.citation_id} citation={c} />
            ))}
          </div>
        ) : (
          <p className="text-stone-700 text-[12.5px] px-1">
            {turn
              ? 'No citations for this answer.'
              : 'Citations for your next question will appear here.'}
          </p>
        )}
      </div>

      <div className="px-5 py-4 border-t border-ink-700">
        <SectionLabel count={turn?.sources.length ?? 0}>Retrieved Passages</SectionLabel>
        <div className="mt-3">
          {turn && turn.sources.length > 0 ? (
            <div className="space-y-2.5">
              {turn.sources.map((s) => (
                <SourceCard key={s.chunk_id} source={s} />
              ))}
            </div>
          ) : (
            <p className="text-stone-700 text-[12.5px]">
              Passages retrieved from your knowledge base will appear here.
            </p>
          )}
        </div>
      </div>

      <div className="px-5 py-4 border-t border-ink-700">
        <SectionLabel>Research Metrics</SectionLabel>
        {done ? (
          <div className="mt-3 grid grid-cols-2 gap-2">
            <MetricTile
              icon={<ClockIcon size={11} />}
              label="Response time"
              value={turn?.durationMs !== undefined ? `${turn.durationMs}ms` : '—'}
            />
            <MetricTile
              icon={<LayersIcon size={11} />}
              label="Passages"
              value={turn?.chunkCount !== undefined ? String(turn.chunkCount) : '—'}
            />
          </div>
        ) : (
          <p className="mt-3 text-stone-700 text-[12.5px]">
            Response time and retrieval counts will appear here once an answer completes.
          </p>
        )}
      </div>

      <div className="px-5 py-4 border-t border-ink-700">
        <SectionLabel>Knowledge Graph</SectionLabel>
        <div className="mt-3 border border-dashed border-ink-600 rounded-lg p-4 flex flex-col items-center text-center gap-2">
          <span className="text-stone-700">
            <NetworkIcon size={18} />
          </span>
          <p className="text-stone-700 text-[11.5px] leading-relaxed">
            Document and topic connections will be visualized here.
          </p>
        </div>
      </div>
    </aside>
  );
}
