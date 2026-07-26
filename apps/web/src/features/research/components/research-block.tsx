'use client';

import type { ReactNode } from 'react';
import type { Citation } from '@/lib/api';
import { isWebCitation, type ResearchTurn } from '@/features/research/types';
import { AlertIcon, ClockIcon, LayersIcon, NetworkIcon } from '@/components/ui/icons';
import { Markdown } from '@/components/ui/markdown';
import { StreamingStatus } from '@/features/research/components/streaming-status';

/** Shared with `DeepResearchBlock` for rendering a rejected report's
 * answer the same way a Linear Research turn's is rendered -- markdown
 * formatting plus inline citation badges (`[S1]`/`[W1-1]`) for any id
 * present in `citations`. */
export function renderAnswer(answer: string, citations: Citation[]): ReactNode {
  return <Markdown content={answer} citations={citations} />;
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
          <div className="text-stone-200 text-sm mb-4">
            {renderAnswer(turn.answer, turn.citations)}
            {turn.stage === 'generating' && (
              <span className="inline-block w-1.5 h-3.5 ml-0.5 bg-sage-500 animate-pulse align-middle" />
            )}
          </div>
        ) : (
          <div className="mb-2">
            <StreamingStatus stage={turn.stage} chunkCount={turn.chunkCount} />
          </div>
        )}

        {turn.stage === 'done' && turn.citations.length === 0 && (
          <div className="flex items-start gap-2.5 mb-4 px-3 py-2 rounded-lg border border-amber-800/40 bg-amber-500/5 text-amber-500 text-[12px]">
            <AlertIcon size={12} className="flex-shrink-0 mt-0.5" />
            <span>
              No matching passages were found in your documents -- this answer is generated from
              general knowledge, not your library.
            </span>
          </div>
        )}

        {turn.citations.length > 0 && (
          <div className="flex items-center gap-1.5 mb-4 flex-wrap">
            {turn.citations.map((c) => {
              const web = isWebCitation(c.citation_id);
              return (
                <span
                  key={c.citation_id}
                  title={web ? `${c.filename} · found via web search` : c.filename}
                  className={`inline-flex items-center gap-1 font-mono text-[11px] px-1.5 py-0.5 rounded border ${
                    web
                      ? 'text-sky-400 border-sky-800/40 bg-sky-500/5'
                      : 'text-amber-500 border-amber-800/40 bg-amber-500/5'
                  }`}
                >
                  {web && <NetworkIcon size={10} />}
                  [{c.citation_id.slice(1)}]
                </span>
              );
            })}
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
