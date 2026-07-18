import type { ResearchHistoryEntry } from '@/features/research/types';
import { MessageIcon } from '@/components/ui/icons';

function formatWhen(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.round(diffMs / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return new Date(iso).toLocaleDateString();
}

export function ResearchSidebar({
  history,
  activeResearchId,
  onSelect,
  onClear,
}: {
  history: ResearchHistoryEntry[];
  activeResearchId: string | null;
  onSelect: (researchId: string) => void;
  onClear: () => void;
}) {
  return (
    <aside className="w-56 flex-shrink-0 border-r border-ink-600 bg-ink-900/50 flex flex-col h-full">
      <div className="px-4 py-4 border-b border-ink-600 flex items-center justify-between">
        <span className="font-mono text-stone-600 text-[10px] tracking-[0.2em] uppercase">
          History
        </span>
        <button
          onClick={onClear}
          title="Clear workspace"
          className="w-5 h-5 rounded flex items-center justify-center text-stone-500 hover:text-sage-400 hover:bg-ink-700 transition-colors"
        >
          +
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto scrollbar-thin px-2 py-2">
        {history.length === 0 ? (
          <p className="px-3 py-4 text-stone-700 text-[12px] leading-relaxed">
            Questions you ask will show up here for this browser.
          </p>
        ) : (
          <ul className="space-y-0.5" role="list">
            {history.map((h) => (
              <li key={h.researchId}>
                <button
                  onClick={() => onSelect(h.researchId)}
                  className={`w-full flex items-start gap-2 px-3 py-2 rounded-md text-left transition-colors duration-100 ${
                    activeResearchId === h.researchId
                      ? 'bg-ink-700 text-stone-100'
                      : 'text-stone-400 hover:text-stone-200 hover:bg-ink-700/60'
                  }`}
                >
                  <span
                    className={`mt-0.5 flex-shrink-0 ${
                      activeResearchId === h.researchId ? 'text-sage-400' : 'text-stone-600'
                    }`}
                  >
                    <MessageIcon size={12} />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-[13px] truncate">{h.query}</span>
                    <span className="block font-mono text-stone-600 text-[10px] mt-0.5">
                      {formatWhen(h.createdAt)}
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </nav>

      <div className="px-4 py-3 border-t border-ink-600">
        <p className="font-mono text-stone-700 text-[10px] leading-relaxed">
          History is stored in this browser only. Folders and sharing are coming soon.
        </p>
      </div>
    </aside>
  );
}
