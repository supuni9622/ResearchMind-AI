import type { ResearchSource } from '@/lib/api';
import { FileTextIcon } from '@/components/ui/icons';

export function SourceCard({ source }: { source: ResearchSource }) {
  const scorePct = Math.round(source.score * 100);

  return (
    <div className="border border-ink-600 rounded-lg p-3.5 hover:border-ink-400 transition-colors duration-100">
      <div className="flex items-start gap-2.5 mb-2.5">
        <FileTextIcon size={12} className="flex-shrink-0 mt-0.5 text-stone-600" />
        <div className="min-w-0 flex-1">
          <p className="text-stone-200 text-[12.5px] font-medium truncate">{source.filename}</p>
          {source.page !== null && (
            <p className="font-mono text-stone-600 text-[10px] mt-0.5">p. {source.page}</p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2">
        <div className="flex-1 h-1 rounded-full bg-ink-700 overflow-hidden">
          <div className="h-full bg-sage-600" style={{ width: `${scorePct}%` }} />
        </div>
        <span className="font-mono text-stone-600 text-[10px] tabular-nums">{scorePct}%</span>
      </div>
    </div>
  );
}
