import type { ResearchTurn } from '@/features/research/types';
import { SectionLabel } from '@/components/ui/page-header';
import { SourceCard } from '@/features/research/components/source-card';
import { NetworkIcon, ShieldIcon, ClockIcon, ZapIcon, TargetIcon } from '@/components/ui/icons';

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
  return (
    <aside className="w-80 flex-shrink-0 border-l border-ink-600 bg-ink-900/50 h-full overflow-y-auto scrollbar-thin">
      <div className="px-5 py-4 border-b border-ink-700">
        <SectionLabel count={turn?.sources.length ?? 0}>Sources</SectionLabel>
      </div>

      <div className="px-4 py-4">
        {turn ? (
          <div className="space-y-2.5">
            {turn.sources.map((s) => (
              <SourceCard key={s.citationId} source={s} />
            ))}
          </div>
        ) : (
          <p className="text-stone-700 text-[12.5px] px-1">
            Sources for your next question will appear here.
          </p>
        )}
      </div>

      <div className="px-5 py-4 border-t border-ink-700">
        <SectionLabel>Research Metrics</SectionLabel>
        {turn ? (
          <div className="mt-3 grid grid-cols-2 gap-2">
            <MetricTile icon={<ClockIcon size={11} />} label="Latency" value={`${turn.metrics.latencyMs}ms`} />
            <MetricTile icon={<ZapIcon size={11} />} label="Tokens" value={turn.metrics.tokens.toLocaleString()} />
            <MetricTile icon={<ZapIcon size={11} />} label="Cost" value={`$${turn.metrics.costUsd.toFixed(3)}`} />
            <MetricTile icon={<TargetIcon size={11} />} label="Grounded" value={`${Math.round(turn.evaluation.groundedness * 100)}%`} />
          </div>
        ) : (
          <p className="mt-3 text-stone-700 text-[12.5px]">
            Latency, cost, and groundedness for each answer will appear here.
          </p>
        )}
        <div className="mt-3 flex items-center gap-1.5 text-stone-700">
          <ShieldIcon size={11} />
          <span className="font-mono text-[10px]">no security warnings</span>
        </div>
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
