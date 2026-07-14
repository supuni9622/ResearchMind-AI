'use client';

import { useRef } from 'react';

export function ResearchComposer({
  value,
  onChange,
  onSubmit,
  loading,
}: {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  loading: boolean;
}) {
  const inputRef = useRef<HTMLTextAreaElement>(null);

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (value.trim() && !loading) onSubmit();
    }
  }

  return (
    <div className="flex-shrink-0 border-t border-ink-600 px-8 py-5 bg-ink-950/80 backdrop-blur-sm">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (value.trim() && !loading) onSubmit();
        }}
        className="max-w-2xl"
      >
        <div className="flex gap-2.5 items-end">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={value}
              onChange={(e) => onChange(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a research question…"
              rows={1}
              disabled={loading}
              className="w-full bg-ink-800 border border-ink-500 rounded-xl px-4 py-2.5 text-stone-100 text-sm placeholder-stone-600 resize-none focus:outline-none focus:border-sage-600 transition-colors min-h-[42px] max-h-36 overflow-y-auto scrollbar-thin"
              style={{ fieldSizing: 'content' } as React.CSSProperties}
            />
          </div>
          <button
            type="submit"
            disabled={!value.trim() || loading}
            className="flex-shrink-0 w-9 h-9 rounded-xl bg-sage-600 hover:bg-sage-500 disabled:bg-ink-700 disabled:text-stone-700 text-stone-100 flex items-center justify-center transition-colors duration-150"
          >
            {loading ? (
              <div className="w-3.5 h-3.5 border border-current/30 border-t-current rounded-full animate-spin" />
            ) : (
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                <path
                  d="M2 7h10M8 3l4 4-4 4"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            )}
          </button>
        </div>
        <p className="mt-1.5 font-mono text-stone-700 text-[10px]">
          Enter to send · Shift + Enter for new line
        </p>
      </form>
    </div>
  );
}
