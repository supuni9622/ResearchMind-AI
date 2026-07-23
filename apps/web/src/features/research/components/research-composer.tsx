'use client';

import { useRef } from 'react';
import type { GenerationProvider } from '@/lib/api';
import { PROVIDER_OPTIONS, type ResearchMode } from '@/features/research/types';
import { SparklesIcon, ZapIcon } from '@/components/ui/icons';

const MODE_OPTIONS: { value: ResearchMode; label: string; icon: typeof ZapIcon; title: string }[] = [
  { value: 'linear', label: 'Linear', icon: ZapIcon, title: 'Fast, one-shot cited answer' },
  {
    value: 'deep',
    label: 'Deep',
    icon: SparklesIcon,
    title: 'Multi-step research report -- plan review, then an approved async run',
  },
];

export function ResearchComposer({
  value,
  onChange,
  onSubmit,
  loading,
  provider,
  onProviderChange,
  mode,
  onModeChange,
}: {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  loading: boolean;
  provider: GenerationProvider | 'auto';
  onProviderChange: (p: GenerationProvider | 'auto') => void;
  mode: ResearchMode;
  onModeChange: (m: ResearchMode) => void;
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
        <div className="flex items-center gap-1 mb-2 w-fit bg-ink-800 border border-ink-600 rounded-lg p-0.5">
          {MODE_OPTIONS.map((opt) => {
            const Icon = opt.icon;
            const active = mode === opt.value;
            return (
              <button
                key={opt.value}
                type="button"
                title={opt.title}
                disabled={loading}
                onClick={() => onModeChange(opt.value)}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md font-mono text-[10px] uppercase tracking-widest transition-colors duration-150 disabled:cursor-not-allowed ${
                  active
                    ? 'bg-sage-600 text-stone-100'
                    : 'text-stone-500 hover:text-stone-300'
                }`}
              >
                <Icon size={11} />
                {opt.label}
              </button>
            );
          })}
        </div>
        <div className="flex gap-2.5 items-end">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={value}
              onChange={(e) => onChange(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                mode === 'deep'
                  ? 'Describe what you want a comprehensive report on…'
                  : 'Ask a research question…'
              }
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
        <div className="mt-1.5 flex items-center justify-between">
          <p className="font-mono text-stone-700 text-[10px]">
            Enter to send · Shift + Enter for new line
          </p>
          <label className="flex items-center gap-1.5">
            <span className="font-mono text-stone-700 text-[10px] uppercase tracking-widest">
              Model
            </span>
            <select
              value={provider}
              onChange={(e) => onProviderChange(e.target.value as GenerationProvider | 'auto')}
              disabled={loading}
              className="bg-ink-800 border border-ink-600 rounded-md px-1.5 py-0.5 font-mono text-stone-400 text-[10px] focus:outline-none focus:border-sage-600 transition-colors"
            >
              {PROVIDER_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </form>
    </div>
  );
}
