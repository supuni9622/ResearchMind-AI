'use client';

import { useState } from 'react';
import type { ChatAttachment, ChatMessage } from '@/features/chat/types';
import { AlertIcon, BookIcon, CloseIcon, NetworkIcon, SparklesIcon } from '@/components/ui/icons';
import { Markdown } from '@/components/ui/markdown';
import { FeedbackControl } from '@/components/ui/feedback-control';

function AttachmentThumbnails({
  attachments,
  onOpen,
}: {
  attachments: ChatAttachment[];
  onOpen: (attachment: ChatAttachment) => void;
}) {
  return (
    <div className="mb-1.5 flex flex-wrap justify-end gap-1.5">
      {attachments.map((attachment) => (
        <button
          key={attachment.id}
          type="button"
          onClick={() => onOpen(attachment)}
          className="block w-16 h-16 rounded-lg overflow-hidden border border-sage-800/40 hover:border-sage-600 transition-colors"
        >
          {/* eslint-disable-next-line @next/next/no-img-element -- presigned S3 URL, not a Next-optimizable local/remote asset */}
          <img
            src={attachment.url}
            alt={attachment.filename}
            className="w-full h-full object-cover"
          />
        </button>
      ))}
    </div>
  );
}

function ImageLightbox({ attachment, onClose }: { attachment: ChatAttachment; onClose: () => void }) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={attachment.filename}
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink-950/90 p-8"
    >
      <button
        type="button"
        onClick={onClose}
        title="Close"
        className="absolute top-4 right-4 w-8 h-8 rounded-full bg-ink-800 border border-ink-600 text-stone-300 hover:text-stone-100 flex items-center justify-center"
      >
        <CloseIcon size={14} />
      </button>
      {/* eslint-disable-next-line @next/next/no-img-element -- presigned S3 URL, not a Next-optimizable local/remote asset */}
      <img
        src={attachment.url}
        alt={attachment.filename}
        onClick={(e) => e.stopPropagation()}
        className="max-w-full max-h-full rounded-lg object-contain"
      />
    </div>
  );
}

function WebSearchStatus({ webSearch }: { webSearch: NonNullable<ChatMessage['webSearch']> }) {
  return (
    <div className="mb-1.5 flex flex-col gap-1">
      <div className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-widest text-stone-600">
        <NetworkIcon size={10} className={webSearch.stage === 'searching' ? 'animate-pulse' : ''} />
        {webSearch.stage === 'searching' ? 'Searching the web…' : 'Searched the web'}
      </div>
      {webSearch.stage === 'done' && webSearch.sources && webSearch.sources.length > 0 && (
        <ul className="flex flex-wrap gap-1.5">
          {webSearch.sources.map((source) => (
            <li key={source.url}>
              <a
                href={source.url}
                target="_blank"
                rel="noopener noreferrer"
                title={source.title}
                className="inline-block px-1.5 py-0.5 rounded-md bg-ink-800 border border-ink-600 text-stone-500 hover:text-sage-400 hover:border-sage-700 text-[10px] font-mono transition-colors"
              >
                {source.domain}
              </a>
            </li>
          ))}
        </ul>
      )}
      {webSearch.stage === 'skipped' && (
        <p className="text-stone-700 text-[11px]">
          Nothing useful turned up — answered from general knowledge instead.
        </p>
      )}
    </div>
  );
}

function PaperSearchStatus({
  paperSearch,
}: {
  paperSearch: NonNullable<ChatMessage['paperSearch']>;
}) {
  return (
    <div className="mb-1.5 flex flex-col gap-1">
      <div className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-widest text-stone-600">
        <BookIcon size={10} className={paperSearch.stage === 'searching' ? 'animate-pulse' : ''} />
        {paperSearch.stage === 'searching' ? 'Searching research papers…' : 'Searched research papers'}
      </div>
      {paperSearch.stage === 'done' && paperSearch.sources && paperSearch.sources.length > 0 && (
        <ul className="flex flex-wrap gap-1.5">
          {paperSearch.sources.map((source) => {
            const label = source.year ? `${source.title} (${source.year})` : source.title;
            const className =
              'inline-block px-1.5 py-0.5 rounded-md bg-ink-800 border border-ink-600 text-stone-500 hover:text-sage-400 hover:border-sage-700 text-[10px] font-mono transition-colors max-w-[220px] truncate';
            return (
              <li key={source.title}>
                {source.url ? (
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    title={label}
                    className={className}
                  >
                    {label}
                  </a>
                ) : (
                  <span title={label} className={className}>
                    {label}
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      )}
      {paperSearch.stage === 'skipped' && (
        <p className="text-stone-700 text-[11px]">
          No matching papers found — answered from general knowledge instead.
        </p>
      )}
    </div>
  );
}

export function MessageBubble({ message }: { message: ChatMessage }) {
  const [openAttachment, setOpenAttachment] = useState<ChatAttachment | null>(null);

  if (message.role === 'user') {
    return (
      <div className="flex flex-col items-end">
        {message.attachments && message.attachments.length > 0 && (
          <AttachmentThumbnails attachments={message.attachments} onOpen={setOpenAttachment} />
        )}
        <div className="flex justify-end">
          <div className="max-w-lg bg-sage-700/25 border border-sage-800/40 rounded-2xl rounded-tr-sm px-4 py-2.5">
            <p className="text-stone-100 text-sm leading-relaxed whitespace-pre-wrap">
              {message.content}
            </p>
          </div>
        </div>
        {openAttachment && (
          <ImageLightbox attachment={openAttachment} onClose={() => setOpenAttachment(null)} />
        )}
      </div>
    );
  }

  return (
    <div className="flex gap-2.5 max-w-2xl">
      <div className="w-6 h-6 rounded-full bg-ink-800 border border-ink-600 flex items-center justify-center flex-shrink-0 mt-0.5 text-sage-500">
        <SparklesIcon size={11} />
      </div>

      {message.stage === 'error' ? (
        <div className="flex items-start gap-2 px-4 py-2.5 rounded-2xl rounded-tl-sm border border-red-800/50 bg-red-900/20 text-red-400 text-[13px]">
          <AlertIcon size={13} className="flex-shrink-0 mt-0.5" />
          <span>{message.error}</span>
        </div>
      ) : (
        <div className="rounded-2xl rounded-tl-sm px-4 py-2.5 bg-ink-800/60">
          {message.webSearch && <WebSearchStatus webSearch={message.webSearch} />}
          {message.paperSearch && <PaperSearchStatus paperSearch={message.paperSearch} />}
          <div className="text-stone-200 text-sm">
            <Markdown content={message.content} />
            {message.stage === 'streaming' && (
              <span className="inline-block w-1.5 h-3.5 ml-0.5 bg-sage-500 animate-pulse align-middle" />
            )}
          </div>
          {message.stage === 'done' && (
            <FeedbackControl
              generationId={message.generationId}
              surface="chat"
              memoryUsed={message.memoryUsed}
              className="mt-2 pt-2 border-t border-ink-700"
            />
          )}
        </div>
      )}
    </div>
  );
}
