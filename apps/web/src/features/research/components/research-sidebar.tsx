import type { ResearchConversationEntry } from '@/features/research/types';
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
  conversations,
  activeConversationId,
  onSelect,
  onNew,
}: {
  conversations: ResearchConversationEntry[];
  activeConversationId: string | null;
  onSelect: (conversationId: string) => void;
  onNew: () => void;
}) {
  return (
    <aside className="w-56 flex-shrink-0 border-r border-ink-600 bg-ink-900/50 flex flex-col h-full">
      <div className="px-4 py-4 border-b border-ink-600 flex items-center justify-between">
        <span className="font-mono text-stone-600 text-[10px] tracking-[0.2em] uppercase">
          History
        </span>
        <button
          onClick={onNew}
          title="Start a new conversation"
          className="w-5 h-5 rounded flex items-center justify-center text-stone-500 hover:text-sage-400 hover:bg-ink-700 transition-colors"
        >
          +
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto scrollbar-thin px-2 py-2">
        {conversations.length === 0 ? (
          <p className="px-3 py-4 text-stone-700 text-[12px] leading-relaxed">
            Conversations you start will show up here.
          </p>
        ) : (
          <ul className="space-y-0.5" role="list">
            {conversations.map((c) => (
              <li key={c.conversationId}>
                <button
                  onClick={() => onSelect(c.conversationId)}
                  className={`w-full flex items-start gap-2 px-3 py-2 rounded-md text-left transition-colors duration-100 ${
                    activeConversationId === c.conversationId
                      ? 'bg-ink-700 text-stone-100'
                      : 'text-stone-400 hover:text-stone-200 hover:bg-ink-700/60'
                  }`}
                >
                  <span
                    className={`mt-0.5 flex-shrink-0 ${
                      activeConversationId === c.conversationId ? 'text-sage-400' : 'text-stone-600'
                    }`}
                  >
                    <MessageIcon size={12} />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-[13px] truncate">{c.title}</span>
                    <span className="block font-mono text-stone-600 text-[10px] mt-0.5">
                      {formatWhen(c.updatedAt)}
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
          Conversations and their questions are saved to your account.
        </p>
      </div>
    </aside>
  );
}
