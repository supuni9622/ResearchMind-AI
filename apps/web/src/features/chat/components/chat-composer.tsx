'use client';

import { useRef, useState } from 'react';
import { api, type GenerationProvider } from '@/lib/api';
import type { VoiceChatStatus } from '@/features/chat/use-chat';
import type { ChatAttachment } from '@/features/chat/types';
import { BookIcon, MicIcon, MicOffIcon, NetworkIcon, PaperclipIcon } from '@/components/ui/icons';
import { useProviderOptions } from '@/hooks/use-provider-options';

const VOICE_STATUS_LABEL: Record<VoiceChatStatus, string> = {
  idle: 'Voice',
  connecting: 'Connecting…',
  listening: 'Listening…',
  speaking: 'Speaking…',
  error: 'Voice error',
};

// Wave 4 chat attachments (docs/PRIORITIZED_ROADMAP.md) -- mirrors
// apps/api/app/ai/runtime/chat/attachments/constants.py.
const MAX_ATTACHMENTS_PER_TURN = 5;
const MAX_ATTACHMENT_SIZE_BYTES = 10 * 1024 * 1024;
const SUPPORTED_ATTACHMENT_TYPES = ['image/png', 'image/jpeg', 'image/webp', 'image/gif'];

interface UploadingAttachment {
  localId: string;
  filename: string;
}

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
  attachments,
  onAttachmentsChange,
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
  attachments: ChatAttachment[];
  // Functional-updater form (mirrors `Dispatch<SetStateAction<...>>`) --
  // parallel uploads each resolve independently and must append against
  // the *latest* list, not whatever `attachments` this closure captured
  // when the batch started.
  onAttachmentsChange: (update: ChatAttachment[] | ((prev: ChatAttachment[]) => ChatAttachment[])) => void;
  voiceStatus: VoiceChatStatus;
  voiceError: string | null;
  voiceDraftTranscript: string;
  onStartVoice: () => void;
  onStopVoice: () => void;
}) {
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const providerOptions = useProviderOptions();
  const voiceActive = voiceStatus !== 'idle' && voiceStatus !== 'error';
  const [uploading, setUploading] = useState<UploadingAttachment[]>([]);
  const [attachmentError, setAttachmentError] = useState<string | null>(null);
  const attachmentSlotsUsed = attachments.length + uploading.length;

  async function handleFilesSelected(files: FileList | null) {
    if (!files || files.length === 0) return;
    setAttachmentError(null);

    const incoming = Array.from(files);
    const availableSlots = MAX_ATTACHMENTS_PER_TURN - attachmentSlotsUsed;
    if (incoming.length > availableSlots) {
      setAttachmentError(
        availableSlots <= 0
          ? `You can attach up to ${MAX_ATTACHMENTS_PER_TURN} images per turn.`
          : `Only ${availableSlots} more image${availableSlots === 1 ? '' : 's'} can be added to this turn.`
      );
    }

    const accepted = incoming.slice(0, Math.max(availableSlots, 0)).filter((file) => {
      if (!SUPPORTED_ATTACHMENT_TYPES.includes(file.type)) {
        setAttachmentError(`${file.name} isn't a supported image type.`);
        return false;
      }
      if (file.size > MAX_ATTACHMENT_SIZE_BYTES) {
        setAttachmentError(`${file.name} is larger than 10MB.`);
        return false;
      }
      return true;
    });

    await Promise.all(
      accepted.map(async (file) => {
        const localId = crypto.randomUUID();
        setUploading((prev) => [...prev, { localId, filename: file.name }]);
        try {
          const uploaded = await api.chat.uploadAttachment(file);
          onAttachmentsChange((prev) => [
            ...prev,
            {
              id: uploaded.id,
              filename: uploaded.filename,
              contentType: uploaded.content_type,
              url: uploaded.url,
            },
          ]);
        } catch (err) {
          setAttachmentError(err instanceof Error ? err.message : 'Upload failed.');
        } finally {
          setUploading((prev) => prev.filter((item) => item.localId !== localId));
        }
      })
    );
  }

  function handleRemoveAttachment(id: string) {
    onAttachmentsChange((prev) => prev.filter((attachment) => attachment.id !== id));
  }

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
        {(attachments.length > 0 || uploading.length > 0) && (
          <div className="mb-1.5 px-1 flex flex-wrap gap-1.5">
            {attachments.map((attachment) => (
              <div key={attachment.id} className="relative w-11 h-11 flex-shrink-0 group">
                {/* eslint-disable-next-line @next/next/no-img-element -- presigned S3 URL, not a Next-optimizable local/remote asset */}
                <img
                  src={attachment.url}
                  alt={attachment.filename}
                  className="w-11 h-11 rounded-lg object-cover border border-ink-600"
                />
                <button
                  type="button"
                  title={`Remove ${attachment.filename}`}
                  onClick={() => handleRemoveAttachment(attachment.id)}
                  className="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full bg-ink-900 border border-ink-600 text-stone-400 hover:text-stone-100 flex items-center justify-center text-[9px] leading-none opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  ×
                </button>
              </div>
            ))}
            {uploading.map((item) => (
              <div
                key={item.localId}
                title={item.filename}
                className="w-11 h-11 flex-shrink-0 rounded-lg border border-ink-600 bg-ink-800 flex items-center justify-center"
              >
                <div className="w-3.5 h-3.5 border border-current/30 border-t-current rounded-full animate-spin text-stone-500" />
              </div>
            ))}
          </div>
        )}
        {attachmentError && (
          <p className="mb-1.5 px-1 font-mono text-[10px] text-red-400">{attachmentError}</p>
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
          <input
            ref={fileInputRef}
            type="file"
            accept={SUPPORTED_ATTACHMENT_TYPES.join(',')}
            multiple
            hidden
            onChange={(e) => {
              void handleFilesSelected(e.target.files);
              e.target.value = '';
            }}
          />
          <button
            type="button"
            title="Attach an image (up to 5 per turn)"
            disabled={loading || attachmentSlotsUsed >= MAX_ATTACHMENTS_PER_TURN}
            onClick={() => fileInputRef.current?.click()}
            className="flex-shrink-0 w-9 h-9 rounded-xl flex items-center justify-center transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-40 bg-ink-800 border border-ink-600 text-stone-400 hover:text-stone-200"
          >
            <PaperclipIcon size={14} />
          </button>
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
