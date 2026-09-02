'use client';

import { useEffect, useRef, useState } from 'react';
import { api, type Document, type GenerationProvider } from '@/lib/api';
import {
  type DeepResearchWebSearchMode,
  type ResearchMode,
} from '@/features/research/types';
import { BookIcon, FileTextIcon, NetworkIcon, SparklesIcon, ZapIcon } from '@/components/ui/icons';
import { useProviderOptions } from '@/hooks/use-provider-options';
import { useActiveProject } from '@/hooks/use-active-project';

/** Finds the "@partial" mention being typed at `cursor`, if any -- the
 * nearest unclosed "@" walking back from the cursor, with no whitespace
 * in between (an "@" followed by a space is a finished word, not a
 * mention-in-progress). Returns the trigger's start index (the "@"
 * itself) and the partial text typed after it, or null when the cursor
 * isn't inside a mention. */
function findMentionTrigger(text: string, cursor: number): { start: number; partial: string } | null {
  const upToCursor = text.slice(0, cursor);
  const at = upToCursor.lastIndexOf('@');
  if (at === -1) return null;
  const partial = upToCursor.slice(at + 1);
  if (/\s/.test(partial)) return null;
  return { start: at, partial };
}

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
  onMentionSelect,
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
  /** Called when the user picks a document from the "@" mention dropdown
   * -- restricts Linear Research retrieval to just this document. Only
   * meaningful in 'linear' mode; the dropdown itself only appears there. */
  onMentionSelect: (doc: { id: string; filename: string }) => void;
}) {
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const providerOptions = useProviderOptions();
  const { activeProjectId } = useActiveProject();

  const [mentionQuery, setMentionQuery] = useState<string | null>(null);
  const [mentionResults, setMentionResults] = useState<Document[]>([]);
  const [mentionIndex, setMentionIndex] = useState(0);
  const mentionOpen = mode === 'linear' && mentionQuery !== null && mentionResults.length > 0;

  useEffect(() => {
    if (mode !== 'linear' || mentionQuery === null) {
      setMentionResults([]);
      return;
    }
    let cancelled = false;
    const timer = setTimeout(() => {
      api.documents
        .list({ search: mentionQuery || undefined, projectId: activeProjectId, limit: 8 })
        .then(({ items }) => {
          if (!cancelled) {
            setMentionResults(items);
            setMentionIndex(0);
          }
        })
        .catch(() => {
          if (!cancelled) setMentionResults([]);
        });
    }, 200);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [mode, mentionQuery, activeProjectId]);

  function handleTextChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    onChange(e.target.value);
    const trigger = findMentionTrigger(e.target.value, e.target.selectionStart ?? e.target.value.length);
    setMentionQuery(trigger?.partial ?? null);
  }

  function selectMention(doc: Document) {
    const cursor = inputRef.current?.selectionStart ?? value.length;
    const trigger = findMentionTrigger(value, cursor);
    if (!trigger) return;
    const before = value.slice(0, trigger.start);
    const after = value.slice(cursor);
    onChange(`${before}@${doc.filename} ${after}`);
    onMentionSelect({ id: doc.id, filename: doc.filename });
    setMentionQuery(null);
    setMentionResults([]);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (mentionOpen) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setMentionIndex((i) => (i + 1) % mentionResults.length);
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setMentionIndex((i) => (i - 1 + mentionResults.length) % mentionResults.length);
        return;
      }
      if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault();
        selectMention(mentionResults[mentionIndex]);
        return;
      }
      if (e.key === 'Escape') {
        e.preventDefault();
        setMentionQuery(null);
        setMentionResults([]);
        return;
      }
    }

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
            {mentionOpen && (
              <div className="absolute bottom-full left-0 mb-1.5 w-72 max-h-48 overflow-y-auto scrollbar-thin bg-ink-800 border border-ink-500 rounded-xl shadow-lg z-10">
                {mentionResults.map((doc, i) => (
                  <button
                    key={doc.id}
                    type="button"
                    onMouseDown={(e) => {
                      // mousedown (not click) fires before the textarea's
                      // blur -- keeps focus/selection intact for selectMention.
                      e.preventDefault();
                      selectMention(doc);
                    }}
                    onMouseEnter={() => setMentionIndex(i)}
                    className={`w-full flex items-center gap-2 px-3 py-2 text-left text-xs text-stone-300 transition-colors ${
                      i === mentionIndex ? 'bg-ink-700' : 'hover:bg-ink-700/60'
                    }`}
                  >
                    <FileTextIcon size={12} className="flex-shrink-0 text-stone-600" />
                    <span className="truncate">{doc.filename}</span>
                  </button>
                ))}
              </div>
            )}
            <textarea
              ref={inputRef}
              value={value}
              onChange={handleTextChange}
              onKeyDown={handleKeyDown}
              placeholder={
                mode === 'deep'
                  ? 'Describe what you want a comprehensive report on…'
                  : 'Ask a question about your uploaded documents… (@ to reference one)'
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
              {providerOptions.map((opt) => (
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
