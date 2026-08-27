'use client';

import { useState } from 'react';
import { api, type FeedbackRating, type FeedbackSurface, type MemoryFeedbackSignal } from '@/lib/api';
import { ThumbsDownIcon, ThumbsUpIcon } from '@/components/ui/icons';

interface FeedbackControlProps {
  /** From the stream's `generation_id` metadata (E21) -- `undefined` while
   * still streaming, or for messages loaded from history where the
   * backend doesn't return it yet. Renders nothing until present, rather
   * than a disabled/broken button. */
  generationId: string | undefined;
  surface: FeedbackSurface;
  memoryUsed?: boolean;
  className?: string;
}

/**
 * Thumbs up/down against `POST /feedback` (EVALUATION_IMPLEMENTATION_TRACKER.md
 * E21). Upsert on the backend (unique on owner_id+generation_id), so
 * re-clicking changes the vote in place rather than erroring -- this
 * component relies on that: it always just re-submits.
 *
 * No toast/notification library exists anywhere in this app (checked) --
 * feedback is a small inline state change next to the buttons themselves,
 * not a global notification.
 */
export function FeedbackControl({ generationId, surface, memoryUsed = false, className }: FeedbackControlProps) {
  const [rating, setRating] = useState<FeedbackRating | null>(null);
  const [submitting, setSubmitting] = useState<FeedbackRating | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showComment, setShowComment] = useState(false);
  const [comment, setComment] = useState('');
  const [commentSaved, setCommentSaved] = useState(false);
  const [memorySignal, setMemorySignal] = useState<MemoryFeedbackSignal | null>(null);
  const [memorySubmitting, setMemorySubmitting] = useState(false);

  if (!generationId) {
    return null;
  }

  const submit = async (next: FeedbackRating, withComment?: string) => {
    setSubmitting(next);
    setError(null);
    try {
      await api.feedback.submit(generationId, surface, next, withComment);
      setRating(next);
      if (withComment !== undefined) {
        setCommentSaved(true);
      }
      if (next === 'down') {
        setShowComment(true);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not submit feedback.');
    } finally {
      setSubmitting(null);
    }
  };

  const submitMemory = async (signal: MemoryFeedbackSignal) => {
    setMemorySubmitting(true);
    setError(null);
    try {
      await api.feedback.submitMemory(generationId, surface, signal);
      setMemorySignal(signal);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not submit memory feedback.');
    } finally {
      setMemorySubmitting(false);
    }
  };

  return (
    <div className={`flex flex-col gap-1.5 ${className ?? ''}`}>
      <div className="flex items-center gap-1.5">
        <span className="text-[11px] text-ink-500">Was this helpful?</span>
        <button
          type="button"
          onClick={() => void submit('up')}
          disabled={submitting !== null}
          aria-pressed={rating === 'up'}
          aria-label="Thumbs up"
          className={`rounded p-1 transition-colors ${
            rating === 'up' ? 'text-emerald-400' : 'text-ink-500 hover:text-ink-200'
          } disabled:opacity-50`}
        >
          <ThumbsUpIcon size={13} filled={rating === 'up'} />
        </button>
        <button
          type="button"
          onClick={() => void submit('down')}
          disabled={submitting !== null}
          aria-pressed={rating === 'down'}
          aria-label="Thumbs down"
          className={`rounded p-1 transition-colors ${
            rating === 'down' ? 'text-red-400' : 'text-ink-500 hover:text-ink-200'
          } disabled:opacity-50`}
        >
          <ThumbsDownIcon size={13} filled={rating === 'down'} />
        </button>
        {rating && !showComment && (
          <span className="text-[11px] text-ink-500">Thanks for the feedback.</span>
        )}
        {error && <span className="text-[11px] text-red-400">{error}</span>}
      </div>

      {showComment && !commentSaved && (
        <div className="flex items-center gap-1.5 pl-1">
          <input
            type="text"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="What went wrong? (optional)"
            maxLength={2000}
            className="w-56 rounded border border-ink-700 bg-ink-900 px-2 py-1 text-[11px] text-ink-200 placeholder:text-ink-600 focus:border-ink-500 focus:outline-none"
          />
          <button
            type="button"
            onClick={() => void submit('down', comment)}
            disabled={submitting !== null || comment.trim().length === 0}
            className="text-[11px] text-ink-400 hover:text-ink-200 disabled:opacity-50"
          >
            Send
          </button>
        </div>
      )}
      {commentSaved && <span className="pl-1 text-[11px] text-ink-500">Comment sent.</span>}
      {memoryUsed && (
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] text-ink-500">Did memory affect this answer?</span>
          <button
            type="button"
            onClick={() => void submitMemory('helped')}
            disabled={memorySubmitting}
            aria-pressed={memorySignal === 'helped'}
            className={`rounded-full border px-2 py-0.5 text-[10px] transition-colors ${memorySignal === 'helped' ? 'border-sage-600 bg-sage-950 text-sage-300' : 'border-ink-700 text-ink-500 hover:text-ink-200'}`}
          >
            Memory helped
          </button>
          <button
            type="button"
            onClick={() => void submitMemory('wrong')}
            disabled={memorySubmitting}
            aria-pressed={memorySignal === 'wrong'}
            className={`rounded-full border px-2 py-0.5 text-[10px] transition-colors ${memorySignal === 'wrong' ? 'border-red-800 bg-red-950/40 text-red-300' : 'border-ink-700 text-ink-500 hover:text-ink-200'}`}
          >
            Memory was wrong
          </button>
        </div>
      )}
    </div>
  );
}
