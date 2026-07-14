import type { SourceRef } from '@/features/research/types';
import { FileTextIcon } from '@/components/ui/icons';

const STRATEGY_LABEL: Record<SourceRef['strategy'], string> = {
  dense: 'Dense',
  sparse: 'Sparse',
  hybrid: 'Hybrid',
  reranked: 'Reranked',
};

const STRATEGY_TONE: Record<SourceRef['strategy'], string> = {
  dense: 'text-sage-400',
  sparse: 'text-amber-400',
  hybrid: 'text-stone-300',
  reranked: 'text-stone-100',
};

export function SourceCard({ source }: { source: SourceRef }) {
  return (
    <div className="border border-ink-600 rounded-lg p-3.5 hover:border-ink-400 transition-colors duration-100">
      <div className="flex items-start gap-2.5 mb-2.5">
        <span className="font-mono text-amber-500 text-[11px] flex-shrink-0 mt-0.5">
          [{source.citationId}]
        </span>
        <div className="min-w-0 flex-1">
          <p className="flex items-center gap-1.5 text-stone-200 text-[12.5px] font-medium truncate">
            <FileTextIcon size={11} className="flex-shrink-0 text-stone-600" />
            {source.documentName}
          </p>
          <p className="font-mono text-stone-600 text-[10px] mt-0.5">p. {source.pages}</p>
        </div>
      </div>

      <p className="text-stone-500 text-[12px] leading-relaxed line-clamp-3 mb-3">
        {source.excerpt}
      </p>

      <div className="flex items-center justify-between font-mono text-[10px]">
        <span className={STRATEGY_TONE[source.strategy]}>{STRATEGY_LABEL[source.strategy]}</span>
        <span className="text-stone-600">score {source.score.toFixed(2)}</span>
      </div>
    </div>
  );
}
