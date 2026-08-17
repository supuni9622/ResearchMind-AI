'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import type { GenerationProvider } from '@/lib/api';
import { useChat } from '@/features/chat/use-chat';
import { ChatSidebar } from '@/features/chat/components/chat-sidebar';
import { MessageBubble } from '@/features/chat/components/message-bubble';
import { ChatComposer } from '@/features/chat/components/chat-composer';
import { EmptyChat } from '@/features/chat/components/empty-chat';

export default function ChatPage() {
  const replaceConversationUrl = useCallback((conversationId: string) => {
    window.history.replaceState(
      null,
      '',
      `/chat?conversation=${encodeURIComponent(conversationId)}`
    );
  }, []);

  const {
    conversations,
    activeConversationId,
    messages,
    sending,
    hasMoreConversations,
    hasOlderMessages,
    loadingMoreConversations,
    loadingOlderMessages,
    send,
    selectConversation,
    newConversation,
    loadMoreConversations,
    loadOlderMessages,
  } = useChat({ onConversationCreated: replaceConversationUrl });
  const [input, setInput] = useState('');
  const [provider, setProvider] = useState<GenerationProvider | 'auto'>('auto');
  const [webSearchEnabled, setWebSearchEnabled] = useState(false);
  const [paperSearchEnabled, setPaperSearchEnabled] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const lastMessageContent = messages[messages.length - 1]?.content;

  useEffect(() => {
    const restoreConversationFromUrl = () => {
      const conversationId = new URLSearchParams(window.location.search).get('conversation');
      if (conversationId) {
        void selectConversation(conversationId);
      } else {
        newConversation();
      }
    };

    restoreConversationFromUrl();
    window.addEventListener('popstate', restoreConversationFromUrl);
    return () => window.removeEventListener('popstate', restoreConversationFromUrl);
  }, [newConversation, selectConversation]);

  const handleSelectConversation = useCallback(
    async (conversationId: string) => {
      await selectConversation(conversationId);
      window.history.pushState(
        null,
        '',
        `/chat?conversation=${encodeURIComponent(conversationId)}`
      );
    },
    [selectConversation]
  );

  const handleNewConversation = useCallback(() => {
    newConversation();
    window.history.pushState(null, '', '/chat');
  }, [newConversation]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length, lastMessageContent]);

  const handleSubmit = useCallback(() => {
    const query = input.trim();
    if (!query || sending) return;
    setInput('');
    void send(query, {
      provider: provider === 'auto' ? undefined : provider,
      webSearchEnabled,
      paperSearchEnabled,
    });
  }, [input, sending, send, provider, webSearchEnabled, paperSearchEnabled]);

  return (
    <div className="flex h-screen">
      <ChatSidebar
        conversations={conversations}
        activeConversationId={activeConversationId}
        onSelect={(conversationId) => void handleSelectConversation(conversationId)}
        onNew={handleNewConversation}
        hasMore={hasMoreConversations}
        loadingMore={loadingMoreConversations}
        onLoadMore={loadMoreConversations}
      />

      <div className="flex-1 min-w-0 flex flex-col">
        <div className="px-8 pt-6 pb-4 border-b border-ink-600 flex-shrink-0">
          <p className="font-mono text-stone-600 text-[10px] tracking-[0.2em] uppercase mb-1">
            AI Assistant
          </p>
          <h1
            className="font-display text-stone-100"
            style={{
              fontSize: '1.5rem',
              fontVariationSettings: "'opsz' 32, 'SOFT' 0, 'WONK' 0",
            }}
          >
            Chat
          </h1>
          <p className="text-stone-500 text-[12px] mt-1">
            Brainstorm freely with web and paper search — not grounded in your uploaded
            documents. For cited, document-grounded answers, use Research.
          </p>
        </div>

        <div className="flex-1 overflow-y-auto px-8 py-6 scrollbar-thin">
          {messages.length === 0 ? (
            <EmptyChat onSuggest={setInput} />
          ) : (
            <div className="max-w-2xl mx-auto space-y-5">
              {hasOlderMessages && (
                <button
                  type="button"
                  onClick={() => void loadOlderMessages()}
                  disabled={loadingOlderMessages}
                  className="block mx-auto text-xs text-stone-500 hover:text-sage-400 disabled:opacity-50"
                >
                  {loadingOlderMessages ? 'Loading earlier messages…' : 'Load earlier messages'}
                </button>
              )}
              {messages.map((message) => (
                <MessageBubble key={message.id} message={message} />
              ))}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        <ChatComposer
          value={input}
          onChange={setInput}
          onSubmit={handleSubmit}
          loading={sending}
          provider={provider}
          onProviderChange={setProvider}
          webSearchEnabled={webSearchEnabled}
          onWebSearchEnabledChange={setWebSearchEnabled}
          paperSearchEnabled={paperSearchEnabled}
          onPaperSearchEnabledChange={setPaperSearchEnabled}
        />
      </div>
    </div>
  );
}
