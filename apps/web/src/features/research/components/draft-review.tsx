'use client';

import { useState } from 'react';
import {
  isWebCitation,
  type DeepResearchDraft,
  type DeepResearchDraftEdit,
} from '@/features/research/types';
import { NetworkIcon } from '@/components/ui/icons';

function draftToEdit(draft: DeepResearchDraft): DeepResearchDraftEdit {
  return {
    title: draft.title,
    abstract: draft.abstract,
    methodology: draft.methodology,
    findings: draft.findings.map((f) => ({ heading: f.heading, content: f.content })),
    discussion: draft.discussion,
    conclusion: draft.conclusion,
  };
}

const inputClass =
  'w-full bg-ink-800 border border-ink-500 rounded-lg px-2.5 py-1.5 text-stone-100 text-[13px] placeholder-stone-600 focus:outline-none focus:border-sage-600';
const textareaClass = `${inputClass} resize-none leading-relaxed`;
const labelClass = 'font-mono text-stone-600 text-[10px] tracking-[0.15em] uppercase mb-1 block';

/**
 * Read-only (by default) preview of a Deep Research draft awaiting
 * approval, with an "Edit" toggle that swaps the text into editable
 * fields. Citation ids/scores/limitations are never editable (see
 * `ResearchDraftEdit` -- keeping them fixed to the original is what lets
 * an edit skip citation-integrity re-validation entirely).
 *
 * `onEditingChange` reports the current edited values (or `null` when not
 * editing) up to the caller on every keystroke, so "Approve report" can
 * read the latest value without this component needing to expose an
 * imperative getter.
 */
export function DraftReview({
  draft,
  onEditingChange,
}: {
  draft: DeepResearchDraft;
  onEditingChange: (edit: DeepResearchDraftEdit | null) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [edit, setEdit] = useState<DeepResearchDraftEdit | null>(null);

  function startEditing() {
    const next = draftToEdit(draft);
    setEdit(next);
    setEditing(true);
    onEditingChange(next);
  }

  function stopEditing() {
    setEditing(false);
    setEdit(null);
    onEditingChange(null);
  }

  function patch(next: Partial<DeepResearchDraftEdit>) {
    setEdit((prev) => {
      if (!prev) return prev;
      const merged = { ...prev, ...next };
      onEditingChange(merged);
      return merged;
    });
  }

  function patchFinding(index: number, field: 'heading' | 'content', value: string) {
    setEdit((prev) => {
      if (!prev) return prev;
      const findings = prev.findings.map((f, i) => (i === index ? { ...f, [field]: value } : f));
      const merged = { ...prev, findings };
      onEditingChange(merged);
      return merged;
    });
  }

  return (
    <div
      onClick={(e) => e.stopPropagation()}
      className="mb-4 rounded-lg border border-ink-700 bg-ink-800/30 p-4 space-y-4"
    >
      <div className="flex items-start justify-between gap-3">
        {editing && edit ? (
          <div className="flex-1">
            <label className={labelClass}>Title</label>
            <input
              value={edit.title}
              onChange={(e) => patch({ title: e.target.value })}
              className={inputClass}
            />
          </div>
        ) : (
          <p className="text-stone-100 text-[14px] font-medium leading-snug flex-1">
            {draft.title}
          </p>
        )}
        <button
          type="button"
          onClick={editing ? stopEditing : startEditing}
          className="font-mono text-[10px] uppercase tracking-widest text-stone-500 hover:text-sage-500 transition-colors flex-shrink-0 mt-0.5"
        >
          {editing ? 'Done editing' : 'Edit'}
        </button>
      </div>

      <div>
        <label className={labelClass}>Abstract</label>
        {editing && edit ? (
          <textarea
            value={edit.abstract}
            onChange={(e) => patch({ abstract: e.target.value })}
            rows={3}
            className={textareaClass}
          />
        ) : (
          <p className="text-stone-300 text-[13px] leading-relaxed whitespace-pre-wrap">
            {draft.abstract}
          </p>
        )}
      </div>

      <div className="space-y-3">
        {(editing && edit ? edit.findings : draft.findings).map((finding, i) => (
          <div key={i}>
            {editing && edit ? (
              <>
                <input
                  value={finding.heading}
                  onChange={(e) => patchFinding(i, 'heading', e.target.value)}
                  className={`${inputClass} mb-1.5 font-medium`}
                />
                <textarea
                  value={finding.content}
                  onChange={(e) => patchFinding(i, 'content', e.target.value)}
                  rows={3}
                  className={textareaClass}
                />
              </>
            ) : (
              <>
                <p className="text-stone-200 text-[13px] font-medium mb-1">{finding.heading}</p>
                <p className="text-stone-400 text-[13px] leading-relaxed whitespace-pre-wrap">
                  {finding.content}
                </p>
              </>
            )}
          </div>
        ))}
      </div>

      <div>
        <label className={labelClass}>Discussion</label>
        {editing && edit ? (
          <textarea
            value={edit.discussion}
            onChange={(e) => patch({ discussion: e.target.value })}
            rows={3}
            className={textareaClass}
          />
        ) : (
          <p className="text-stone-400 text-[13px] leading-relaxed whitespace-pre-wrap">
            {draft.discussion}
          </p>
        )}
      </div>

      <div>
        <label className={labelClass}>Conclusion</label>
        {editing && edit ? (
          <textarea
            value={edit.conclusion}
            onChange={(e) => patch({ conclusion: e.target.value })}
            rows={2}
            className={textareaClass}
          />
        ) : (
          <p className="text-stone-400 text-[13px] leading-relaxed whitespace-pre-wrap">
            {draft.conclusion}
          </p>
        )}
      </div>

      {draft.limitations.length > 0 && (
        <div>
          <label className={labelClass}>Limitations</label>
          <ul className="list-disc list-inside space-y-0.5">
            {draft.limitations.map((limitation, i) => (
              <li key={i} className="text-stone-400 text-[13px] leading-relaxed">
                {limitation}
              </li>
            ))}
          </ul>
        </div>
      )}

      {draft.review.gap_questions.length > 0 && (
        <div>
          <label className={labelClass}>Open questions from review</label>
          <ul className="list-disc list-inside space-y-0.5">
            {draft.review.gap_questions.map((question, i) => (
              <li key={i} className="text-stone-400 text-[13px] leading-relaxed">
                {question}
              </li>
            ))}
          </ul>
        </div>
      )}

      {draft.citations.length > 0 && (
        <div>
          <label className={labelClass}>Sources</label>
          <div className="flex flex-wrap gap-1.5">
            {draft.citations.map((c) => {
              const web = isWebCitation(c.citation_id);
              return (
                <span
                  key={c.citation_id}
                  title={web ? `${c.excerpt} · found via web search` : c.excerpt}
                  className={`inline-flex items-center gap-1 font-mono text-[11px] px-1.5 py-0.5 rounded border ${
                    web
                      ? 'text-sky-400 border-sky-800/40 bg-sky-500/5'
                      : 'text-amber-500 border-amber-800/40 bg-amber-500/5'
                  }`}
                >
                  {web && <NetworkIcon size={10} />}
                  [{c.citation_id.slice(1)}] {c.filename}
                </span>
              );
            })}
          </div>
        </div>
      )}

      <p className="font-mono text-[10px] text-stone-600 pt-2 border-t border-ink-700">
        Quality review: {draft.review.decision} · citation integrity{' '}
        {Math.round(draft.review.citation_integrity_score * 100)}% · completeness{' '}
        {Math.round(draft.review.completeness_score * 100)}%
        {draft.review.model_quality_score !== null && (
          <> · model quality {Math.round(draft.review.model_quality_score * 100)}%</>
        )}
      </p>
      {draft.review.limitations.length > 0 && (
        <p className="font-mono text-[10px] text-stone-600">
          Reviewer notes: {draft.review.limitations.join(' · ')}
        </p>
      )}
    </div>
  );
}
