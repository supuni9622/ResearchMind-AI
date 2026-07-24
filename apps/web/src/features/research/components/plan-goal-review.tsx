'use client';

import { useState } from 'react';
import type { DeepResearchPendingPlan } from '@/features/research/types';

const inputClass =
  'w-full bg-ink-800 border border-ink-500 rounded-lg px-2.5 py-1.5 text-stone-100 text-[13px] placeholder-stone-600 focus:outline-none focus:border-sage-600';
const textareaClass = `${inputClass} resize-none leading-relaxed`;
const labelClass = 'font-mono text-stone-600 text-[10px] tracking-[0.15em] uppercase mb-1 block';

/**
 * Read-only (by default) preview of the plan and gathered evidence awaiting
 * approval before synthesis runs, with an "Edit" toggle for the one field
 * that's actually still safe to change at this point -- the goal driving
 * synthesis. `tasks` aren't editable here: retrieval for them already ran
 * to produce the evidence being shown, so changing them now wouldn't
 * retroactively affect what was gathered (see
 * `ResearchRunService.record_plan_decision`).
 *
 * `onEditingChange` reports the current edited goal (or `null` when not
 * editing) up to the caller on every keystroke, mirroring `DraftReview`.
 */
export function PlanGoalReview({
  plan,
  onEditingChange,
}: {
  plan: DeepResearchPendingPlan;
  onEditingChange: (editedGoal: string | null) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [goal, setGoal] = useState('');
  const displayedGoal = plan.rewritten_goal ?? plan.goal;

  function startEditing() {
    setGoal(displayedGoal);
    setEditing(true);
    onEditingChange(displayedGoal);
  }

  function stopEditing() {
    setEditing(false);
    setGoal('');
    onEditingChange(null);
  }

  function patchGoal(value: string) {
    setGoal(value);
    onEditingChange(value);
  }

  return (
    <div
      onClick={(e) => e.stopPropagation()}
      className="mb-4 rounded-lg border border-ink-700 bg-ink-800/30 p-4 space-y-4"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <label className={labelClass}>Goal driving the report</label>
          {editing ? (
            <textarea
              value={goal}
              onChange={(e) => patchGoal(e.target.value)}
              rows={2}
              className={textareaClass}
            />
          ) : (
            <p className="text-stone-100 text-[14px] leading-snug">{displayedGoal}</p>
          )}
        </div>
        <button
          type="button"
          onClick={editing ? stopEditing : startEditing}
          className="font-mono text-[10px] uppercase tracking-widest text-stone-500 hover:text-sage-500 transition-colors flex-shrink-0 mt-0.5"
        >
          {editing ? 'Done editing' : 'Edit'}
        </button>
      </div>

      <div>
        <label className={labelClass}>Evidence gathered</label>
        <p className="text-stone-400 text-[13px]">
          {plan.evidence.completed_task_count} task
          {plan.evidence.completed_task_count === 1 ? '' : 's'} completed
          {plan.evidence.failed_task_count > 0 && `, ${plan.evidence.failed_task_count} failed`}
          {plan.evidence.warning_count > 0 &&
            ` · ${plan.evidence.warning_count} warning${plan.evidence.warning_count === 1 ? '' : 's'}`}
        </p>
      </div>

      <ul className="space-y-1.5">
        {plan.tasks.map((task) => (
          <li key={task.task_id} className="text-[13px] text-stone-500">
            · {task.question}
          </li>
        ))}
      </ul>

      {plan.citations.length > 0 && (
        <div>
          <label className={labelClass}>Sources found so far</label>
          <div className="flex flex-wrap gap-1.5">
            {plan.citations.map((c) => (
              <span
                key={c.citation_id}
                title={c.excerpt}
                className="font-mono text-amber-500 text-[11px] px-1.5 py-0.5 rounded border border-amber-800/40 bg-amber-500/5"
              >
                [{c.citation_id.slice(1)}] {c.filename}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
