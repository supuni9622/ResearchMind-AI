import type { Citation } from '@/lib/api';
import { isWebCitation, relevanceScorePercent } from '@/features/research/types';
import { FileTextIcon, NetworkIcon } from '@/components/ui/icons';

export function CitationCard({
  citation,
}: {
  citation: Citation;
}) {
  const web = isWebCitation(citation.citation_id);
  const scorePct = relevanceScorePercent(citation.score);
  return (
    <div className="border border-ink-600 rounded-lg p-3.5 hover:border-ink-400 transition-colors duration-100">
      <div className="flex items-start gap-2.5">
        <span
          className={`font-mono text-[11px] flex-shrink-0 mt-0.5 ${web ? 'text-sky-400' : 'text-amber-500'}`}
        >
          [{citation.citation_id.slice(1)}]
        </span>
        <div className="min-w-0 flex-1">
          <p className="flex items-center gap-1.5 text-stone-200 text-[12.5px] font-medium truncate">
            {web ? (
              <NetworkIcon size={11} className="flex-shrink-0 text-sky-500" />
            ) : (
              <FileTextIcon size={11} className="flex-shrink-0 text-stone-600" />
            )}
            {citation.filename}
            {web && (
              <span className="font-mono text-sky-500 text-[9px] uppercase tracking-widest border border-sky-800/40 bg-sky-500/5 rounded px-1 py-px flex-shrink-0">
                Web
              </span>
            )}
          </p>
          {citation.heading && (
            <p className="text-stone-500 text-[11.5px] mt-1 truncate">{citation.heading}</p>
          )}
          {citation.page_numbers.length > 0 && (
            <p className="font-mono text-stone-600 text-[10px] mt-1">
              p. {citation.page_numbers.join(', ')}
            </p>
          )}
          <div className="flex items-center gap-2 mt-2">
            <div className="flex-1 h-1 rounded-full bg-ink-700 overflow-hidden">
              <div className="h-full bg-sage-600" style={{ width: `${scorePct}%` }} />
            </div>
            <span className="font-mono text-stone-600 text-[10px] tabular-nums">{scorePct}%</span>
          </div>
        </div>
      </div>
    </div>
  );
}
