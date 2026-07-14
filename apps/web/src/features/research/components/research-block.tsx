'use client';

import { useState } from 'react';
import type { ResearchTurn } from '@/features/research/types';
import { ChevronDownIcon, ChevronRightIcon, TargetIcon, CheckCircleIcon } from '@/components/ui/icons';

export function ResearchBlock({
  turn,
  focused,
  onFocus,
}: {
  turn: ResearchTurn;
  focused: boolean;
  onFocus: () => void;
}) {
  const [planOpen, setPlanOpen] = useState(false);

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
        <p className="text-stone-100 text-[15px] leading-snug">{turn.question}</p>
      </div>

      <div className="px-5 py-4">
        <button
          onClick={(e) => {
            e.stopPropagation();
            setPlanOpen((v) => !v);
          }}
          className="flex items-center gap-1.5 text-stone-500 hover:text-stone-300 transition-colors mb-3"
        >
          {planOpen ? <ChevronDownIcon size={10} /> : <ChevronRightIcon size={10} />}
          <span className="font-mono text-[10px] tracking-widest uppercase">Research Plan</span>
          <span className="font-mono text-stone-700 text-[10px]">{turn.planSteps.length} steps</span>
        </button>

        {planOpen && (
          <ol className="space-y-1.5 mb-4 pl-1">
            {turn.planSteps.map((step, i) => (
              <li key={step.id} className="flex items-start gap-2.5">
                <span className="font-mono text-stone-700 text-[10px] mt-0.5 flex-shrink-0">
                  {i + 1}
                </span>
                <span className="text-stone-400 text-[12.5px] leading-relaxed">{step.label}</span>
              </li>
            ))}
          </ol>
        )}

        <p className="text-stone-200 text-sm leading-relaxed mb-4">{turn.answer}</p>

        <div className="flex items-center gap-1.5 mb-4">
          {turn.sources.map((s) => (
            <span
              key={s.citationId}
              className="font-mono text-amber-500 text-[11px] px-1.5 py-0.5 rounded border border-amber-800/40 bg-amber-500/5"
            >
              [{s.citationId}]
            </span>
          ))}
        </div>

        <div className="flex items-center gap-4 pt-3 border-t border-ink-700">
          <span className="flex items-center gap-1.5 text-stone-600">
            <TargetIcon size={11} />
            <span className="font-mono text-[10px]">
              groundedness {Math.round(turn.evaluation.groundedness * 100)}%
            </span>
          </span>
          <span className="flex items-center gap-1.5 text-stone-600">
            <CheckCircleIcon size={11} />
            <span className="font-mono text-[10px]">
              faithfulness {Math.round(turn.evaluation.faithfulness * 100)}%
            </span>
          </span>
          <button
            disabled
            title="Report generation is coming soon"
            className="ml-auto font-mono text-[10px] text-stone-700 cursor-not-allowed"
          >
            generate report →
          </button>
        </div>
      </div>
    </div>
  );
}
