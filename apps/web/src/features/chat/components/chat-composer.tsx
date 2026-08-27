'use client';

import { useRef } from 'react';
import type { GenerationProvider } from '@/lib/api';
import type { VoiceChatStatus } from '@/features/chat/use-chat';
import { BookIcon, MicIcon, MicOffIcon, NetworkIcon } from '@/components/ui/icons';
import { useProviderOptions } from '@/hooks/use-provider-options';

const VOICE_STATUS_LABEL: Record<VoiceChatStatus, string> = {
  idle: 'Voice',
  connecting: 'Connecting…',
  listening: 'Listening…',
  speaking: 'Speaking…',
  error: 'Voice error',
};

export function ChatComposer({
  value,
  onChange,
  onSubmit,
  loading,
  provider,
  onProviderChange,
  webSearchEnabled,
  onWebSearchEnabledChange,
  paperSearchEnabled,
  onPaperSearchEnabledChange,
  voiceStatus,
  voiceError,
  voiceDraftTranscript,
  onStartVoice,
  onStopVoice,
}: {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  loading: boolean;
  provider: GenerationProvider | 'auto';
  onProviderChange: (p: GenerationProvider | 'auto') => void;
  webSearchEnabled: boolean;
  onWebSearchEnabledChange: (v: boolean) => void;
  paperSearchEnabled: boolean;
  onPaperSearchEnabledChange: (v: boolean) => void;
  voiceStatus: VoiceChatStatus;
  voiceError: string | null;
  voiceDraftTranscript: string;
  onStartVoice: () => void;
  onStopVoice: () => void;
}) {
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const providerOptions = useProviderOptions();
  const voiceActive = voiceStatus !== 'idle' && voiceStatus !== 'error';

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
        className="max-w-2xl mx-auto"
      >
        {(voiceActive || voiceDraftTranscript || voiceError) && (
          <div className="mb-1.5 px-1 flex items-center justify-between font-mono text-[10px]">
            <span className={voiceError ? 'text-red-400' : 'text-sage-400'}>
              {voiceError ?? VOICE_STATUS_LABEL[voiceStatus]}
              {voiceDraftTranscript ? ` — "${voiceDraftTranscript}"` : ''}
            </span>
          </div>
        )}
        <div className="flex gap-2.5 items-end">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={value}
              onChange={(e) => onChange(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Brainstorm an idea, ask a question, or search the web and papers…"
              rows={1}
              disabled={loading}
              className="w-full bg-ink-800 border border-ink-500 rounded-xl px-4 py-2.5 text-stone-100 text-sm placeholder-stone-600 resize-none focus:outline-none focus:border-sage-600 transition-colors min-h-[42px] max-h-36 overflow-y-auto scrollbar-thin"
              style={{ fieldSizing: 'content' } as React.CSSProperties}
            />
          </div>
          <button
            type="button"
            title={voiceActive ? 'Stop voice' : 'Talk to the assistant (T13 — unverified in a real browser yet)'}
            disabled={loading && !voiceActive}
            onClick={() => (voiceActive ? onStopVoice() : onStartVoice())}
            className={`flex-shrink-0 w-9 h-9 rounded-xl flex items-center justify-center transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-40 ${
              voiceActive
                ? 'bg-red-500/90 hover:bg-red-500 text-stone-100'
                : 'bg-ink-800 border border-ink-600 text-stone-400 hover:text-stone-200'
            }`}
          >
            {voiceActive ? <MicOffIcon size={14} /> : <MicIcon size={14} />}
          </button>
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
          <div className="flex items-center gap-3">
            <button
              type="button"
              title="Let the agent search the web for this turn — useful for recent developments your library won't have"
              disabled={loading}
              onClick={() => onWebSearchEnabledChange(!webSearchEnabled)}
              className={`flex items-center gap-1.5 px-2 py-0.5 rounded-md font-mono text-[10px] uppercase tracking-widest transition-colors duration-150 disabled:cursor-not-allowed ${
                webSearchEnabled
                  ? 'bg-sage-600 text-stone-100'
                  : 'bg-ink-800 border border-ink-600 text-stone-600 hover:text-stone-300'
              }`}
            >
              <NetworkIcon size={11} />
              Web search
            </button>
            <button
              type="button"
              title="Search published research papers relevant to this turn — for discovering new papers, not your uploaded library"
              disabled={loading}
              onClick={() => onPaperSearchEnabledChange(!paperSearchEnabled)}
              className={`flex items-center gap-1.5 px-2 py-0.5 rounded-md font-mono text-[10px] uppercase tracking-widest transition-colors duration-150 disabled:cursor-not-allowed ${
                paperSearchEnabled
                  ? 'bg-sage-600 text-stone-100'
                  : 'bg-ink-800 border border-ink-600 text-stone-600 hover:text-stone-300'
              }`}
            >
              <BookIcon size={11} />
              Papers
            </button>
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
        </div>
      </form>
    </div>
  );
}
