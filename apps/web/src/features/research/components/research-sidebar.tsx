import type { ResearchSessionMeta } from '@/features/research/types';
import { MessageIcon } from '@/components/ui/icons';

export function ResearchSidebar({
  sessions,
  activeId,
  onSelect,
  onCreate,
}: {
  sessions: ResearchSessionMeta[];
  activeId: string;
  onSelect: (id: string) => void;
  onCreate: () => void;
}) {
  return (
    <aside className="w-56 flex-shrink-0 border-r border-ink-600 bg-ink-900/50 flex flex-col h-full">
      <div className="px-4 py-4 border-b border-ink-600 flex items-center justify-between">
        <span className="font-mono text-stone-600 text-[10px] tracking-[0.2em] uppercase">
          Research
        </span>
        <button
          onClick={onCreate}
          title="New research session"
          className="w-5 h-5 rounded flex items-center justify-center text-stone-500 hover:text-sage-400 hover:bg-ink-700 transition-colors"
        >
          +
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto scrollbar-thin px-2 py-2">
        <ul className="space-y-0.5" role="list">
          {sessions.map((s) => (
            <li key={s.id}>
              <button
                onClick={() => onSelect(s.id)}
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-md text-[13px] text-left transition-colors duration-100 ${
                  activeId === s.id
                    ? 'bg-ink-700 text-stone-100'
                    : 'text-stone-400 hover:text-stone-200 hover:bg-ink-700/60'
                }`}
              >
                <span className={activeId === s.id ? 'text-sage-400' : 'text-stone-600'}>
                  <MessageIcon size={12} />
                </span>
                <span className="truncate">{s.title}</span>
              </button>
            </li>
          ))}
        </ul>
      </nav>

      <div className="px-4 py-3 border-t border-ink-600">
        <p className="font-mono text-stone-700 text-[10px] leading-relaxed">
          Folders, pinning, and sharing are coming soon.
        </p>
      </div>
    </aside>
  );
}
