import type { ChatMessage } from '@/features/chat/types';
import { AlertIcon, SparklesIcon } from '@/components/ui/icons';

export function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-lg bg-sage-700/25 border border-sage-800/40 rounded-2xl rounded-tr-sm px-4 py-2.5">
          <p className="text-stone-100 text-sm leading-relaxed whitespace-pre-wrap">
            {message.content}
          </p>
        </div>
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
          <p className="text-stone-200 text-sm leading-relaxed whitespace-pre-wrap">
            {message.content}
            {message.stage === 'streaming' && (
              <span className="inline-block w-1.5 h-3.5 ml-0.5 bg-sage-500 animate-pulse align-middle" />
            )}
          </p>
        </div>
      )}
    </div>
  );
}
