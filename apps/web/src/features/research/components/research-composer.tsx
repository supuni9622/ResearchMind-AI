'use client';

import { useRef } from 'react';
import type { GenerationProvider } from '@/lib/api';
import {
  PROVIDER_OPTIONS,
  type DeepResearchWebSearchMode,
  type ResearchMode,
} from '@/features/research/types';
import { BookIcon, NetworkIcon, SparklesIcon, ZapIcon } from '@/components/ui/icons';

const MODE_OPTIONS: { value: ResearchMode; label: string; icon: typeof ZapIcon; title: string }[] = [
  {
    value: 'linear',
    label: 'Linear',
    icon: ZapIcon,
    title: 'Grounded in your uploaded documents only -- fast, one-shot, cost-effective',
  },
  {
    value: 'deep',
    label: 'Deep',
    icon: SparklesIcon,
    title:
      'Agentic multi-step report with web + paper search -- you approve the plan and the final draft before anything publishes',
  },
];

// Cycles DISABLED -> AUTO -> REQUIRED -> DISABLED. AUTO: the agent decides
// whether it needs the web, and asks for approval unless pre-authorized.
// REQUIRED: always includes at least one web source, never asks.
const WEB_SEARCH_OPTIONS: {
  value: DeepResearchWebSearchMode;
  label: string;
  title: string;
}[] = [
  { value: 'disabled', label: 'Off', title: 'Never search the web' },
  {
    value: 'auto',
    label: 'Auto',
    title: 'The agent decides if it needs the web, and asks before searching',
  },
  { value: 'required', label: 'Required', title: 'Always include at least one web source' },
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
  webSearchMode,
  onWebSearchModeChange,
  webSearchAutoApprove,
  onWebSearchAutoApproveChange,
  paperSuggestionsEnabled,
  onPaperSuggestionsEnabledChange,
}: {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  loading: boolean;
  provider: GenerationProvider | 'auto';
  onProviderChange: (p: GenerationProvider | 'auto') => void;
  mode: ResearchMode;
  onModeChange: (m: ResearchMode) => void;
  webSearchMode: DeepResearchWebSearchMode;
  onWebSearchModeChange: (m: DeepResearchWebSearchMode) => void;
  webSearchAutoApprove: boolean;
  onWebSearchAutoApproveChange: (v: boolean) => void;
  paperSuggestionsEnabled: boolean;
  onPaperSuggestionsEnabledChange: (v: boolean) => void;
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
        {mode === 'deep' && (
          <div className="flex items-center gap-2 mb-2">
            <span className="font-mono text-stone-700 text-[10px] uppercase tracking-widest">
              Web search
            </span>
            <div className="flex items-center gap-1 w-fit bg-ink-800 border border-ink-600 rounded-lg p-0.5">
              {WEB_SEARCH_OPTIONS.map((opt) => {
                const active = webSearchMode === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    title={opt.title}
                    disabled={loading}
                    onClick={() => onWebSearchModeChange(opt.value)}
                    className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md font-mono text-[10px] uppercase tracking-widest transition-colors duration-150 disabled:cursor-not-allowed ${
                      active ? 'bg-sage-600 text-stone-100' : 'text-stone-500 hover:text-stone-300'
                    }`}
                  >
                    {opt.value === 'disabled' && <NetworkIcon size={11} />}
                    {opt.label}
                  </button>
                );
              })}
            </div>
            {webSearchMode === 'auto' && (
              <label
                title="When the agent decides it needs the web, proceed without asking for approval"
                className="flex items-center gap-1.5 cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={webSearchAutoApprove}
                  disabled={loading}
                  onChange={(e) => onWebSearchAutoApproveChange(e.target.checked)}
                  className="accent-sage-600"
                />
                <span className="font-mono text-stone-600 text-[10px] uppercase tracking-widest">
                  Skip approval
                </span>
              </label>
            )}
            <label
              title="Suggest related papers via the Research Intelligence MCP server after the report finishes -- non-blocking, never gates the run"
              className="flex items-center gap-1.5 cursor-pointer"
            >
              <input
                type="checkbox"
                checked={paperSuggestionsEnabled}
                disabled={loading}
                onChange={(e) => onPaperSuggestionsEnabledChange(e.target.checked)}
                className="accent-sage-600"
              />
              <BookIcon size={11} className="text-stone-600" />
              <span className="font-mono text-stone-600 text-[10px] uppercase tracking-widest">
                Suggest papers
              </span>
            </label>
          </div>
        )}
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
                  : 'Ask a question about your uploaded documents…'
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
