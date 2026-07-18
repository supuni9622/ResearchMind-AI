'use client';

import type { ReactNode } from 'react';
import type { Citation } from '@/lib/api';
import type { ResearchTurn } from '@/features/research/types';
import { AlertIcon, ClockIcon, LayersIcon } from '@/components/ui/icons';
import { StreamingStatus } from '@/features/research/components/streaming-status';

const CITATION_TOKEN = /\[?(S\d+)\]?/g;

function renderAnswer(answer: string, citations: Citation[]): ReactNode[] {
  const knownIds = new Set(citations.map((c) => c.citation_id));
  if (knownIds.size === 0) return [answer];

  const parts: ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let key = 0;

  while ((match = CITATION_TOKEN.exec(answer)) !== null) {
    const id = match[1];
    if (!knownIds.has(id)) continue;
    parts.push(answer.slice(lastIndex, match.index));
    parts.push(
      <span
        key={key++}
        className="font-mono text-amber-500 text-[0.82em] px-1 py-0.5 rounded border border-amber-800/40 bg-amber-500/5 whitespace-nowrap"
      >
        [{id.slice(1)}]
      </span>
    );
    lastIndex = match.index + match[0].length;
  }
  parts.push(answer.slice(lastIndex));
  return parts;
}

export function ResearchBlock({
  turn,
  focused,
  onFocus,
}: {
  turn: ResearchTurn;
  focused: boolean;
  onFocus: () => void;
}) {
  return (
    <div
      onClick={onFocus}
      className={`border rounded-xl overflow-hidden transition-colors duration-150 cursor-pointer ${
        focused ? 'border-sage-700/60' : 'border-ink-600 hover:border-ink-500'
      }`}
    >
      <div className="px-5 py-4 border-b border-ink-700 bg-ink-800/40">
        <p className="font-mono text-stone-600 text-[10px] tracking-[0.2em] uppercase mb-1.5">
          Question
        </p>
        <p className="text-stone-100 text-[15px] leading-snug">{turn.query}</p>
      </div>

      <div className="px-5 py-4">
        {turn.stage === 'error' ? (
          <div className="flex items-start gap-2.5 px-4 py-3 rounded-lg border border-red-800/50 bg-red-900/20 text-red-400 text-[13px]">
            <AlertIcon size={13} className="flex-shrink-0 mt-0.5" />
            <span>{turn.error}</span>
          </div>
        ) : turn.answer ? (
          <p className="text-stone-200 text-sm leading-relaxed mb-4 whitespace-pre-wrap">
            {renderAnswer(turn.answer, turn.citations)}
            {turn.stage === 'generating' && (
              <span className="inline-block w-1.5 h-3.5 ml-0.5 bg-sage-500 animate-pulse align-middle" />
            )}
          </p>
        ) : (
          <div className="mb-2">
            <StreamingStatus stage={turn.stage} chunkCount={turn.chunkCount} />
          </div>
        )}

        {turn.citations.length > 0 && (
          <div className="flex items-center gap-1.5 mb-4 flex-wrap">
            {turn.citations.map((c) => (
              <span
                key={c.citation_id}
                title={c.filename}
                className="font-mono text-amber-500 text-[11px] px-1.5 py-0.5 rounded border border-amber-800/40 bg-amber-500/5"
              >
                [{c.citation_id.slice(1)}]
              </span>
            ))}
          </div>
        )}

        {turn.stage === 'done' && (
          <div className="flex items-center gap-4 pt-3 border-t border-ink-700">
            {turn.durationMs !== undefined && (
              <span className="flex items-center gap-1.5 text-stone-600">
                <ClockIcon size={11} />
                <span className="font-mono text-[10px]">{turn.durationMs}ms</span>
              </span>
            )}
            {turn.chunkCount !== undefined && (
              <span className="flex items-center gap-1.5 text-stone-600">
                <LayersIcon size={11} />
                <span className="font-mono text-[10px]">{turn.chunkCount} passages searched</span>
              </span>
            )}
            <button
              disabled
              title="Report generation is coming soon"
              className="ml-auto font-mono text-[10px] text-stone-700 cursor-not-allowed"
            >
              generate report →
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
