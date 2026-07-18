import type { Citation } from '@/lib/api';
import { FileTextIcon } from '@/components/ui/icons';

export function CitationCard({ citation }: { citation: Citation }) {
  return (
    <div className="border border-ink-600 rounded-lg p-3.5 hover:border-ink-400 transition-colors duration-100">
      <div className="flex items-start gap-2.5">
        <span className="font-mono text-amber-500 text-[11px] flex-shrink-0 mt-0.5">
          [{citation.citation_id.slice(1)}]
        </span>
        <div className="min-w-0 flex-1">
          <p className="flex items-center gap-1.5 text-stone-200 text-[12.5px] font-medium truncate">
            <FileTextIcon size={11} className="flex-shrink-0 text-stone-600" />
            {citation.filename}
          </p>
          {citation.heading && (
            <p className="text-stone-500 text-[11.5px] mt-1 truncate">{citation.heading}</p>
          )}
          {citation.page_numbers.length > 0 && (
            <p className="font-mono text-stone-600 text-[10px] mt-1">
              p. {citation.page_numbers.join(', ')}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
