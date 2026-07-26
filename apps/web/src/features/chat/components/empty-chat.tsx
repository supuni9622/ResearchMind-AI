import { MessageIcon } from '@/components/ui/icons';

const SUGGESTIONS = [
  'Help me brainstorm angles for a research question on…',
  'What papers should I be reading on this topic?',
  'What are the recent developments in this field?',
  'Poke holes in this hypothesis before I commit to it.',
];

export function EmptyChat({ onSuggest }: { onSuggest: (q: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full max-w-sm mx-auto text-center">
      <div className="w-12 h-12 rounded-xl bg-ink-800 border border-ink-600 flex items-center justify-center mb-4 text-stone-600">
        <MessageIcon size={18} />
      </div>
      <h2 className="text-stone-300 text-sm font-medium mb-2">Your open research space</h2>
      <p className="text-stone-500 text-[13px] mb-8 leading-relaxed">
        Brainstorm ideas, search the web, and find papers worth reading — nothing here is
        grounded in your uploaded library. Found something worth keeping? Download it and add it
        to Documents, then ask about it in Research.
      </p>
      <div className="w-full space-y-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => onSuggest(s)}
            className="w-full text-left px-4 py-3 border border-ink-600 rounded-lg text-stone-400 text-[13px] hover:border-ink-400 hover:text-stone-200 hover:bg-ink-800/50 transition-all duration-100"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
