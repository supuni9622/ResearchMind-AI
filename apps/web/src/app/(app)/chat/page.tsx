'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import type { GenerationProvider } from '@/lib/api';
import { useChat } from '@/features/chat/use-chat';
import { ChatSidebar } from '@/features/chat/components/chat-sidebar';
import { MessageBubble } from '@/features/chat/components/message-bubble';
import { ChatComposer } from '@/features/chat/components/chat-composer';
import { EmptyChat } from '@/features/chat/components/empty-chat';

export default function ChatPage() {
  const {
    conversations,
    activeConversationId,
    messages,
    sending,
    send,
    selectConversation,
    newConversation,
    deleteConversation,
  } = useChat();
  const [input, setInput] = useState('');
  const [provider, setProvider] = useState<GenerationProvider | 'auto'>('auto');
  const bottomRef = useRef<HTMLDivElement>(null);

  const lastMessageContent = messages[messages.length - 1]?.content;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length, lastMessageContent]);

  const handleSubmit = useCallback(() => {
    const query = input.trim();
    if (!query || sending) return;
    setInput('');
    void send(query, { provider: provider === 'auto' ? undefined : provider });
  }, [input, sending, send, provider]);

  return (
    <div className="flex h-screen">
      <ChatSidebar
        conversations={conversations}
        activeConversationId={activeConversationId}
        onSelect={selectConversation}
        onNew={newConversation}
        onDelete={deleteConversation}
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
        </div>

        <div className="flex-1 overflow-y-auto px-8 py-6 scrollbar-thin">
          {messages.length === 0 ? (
            <EmptyChat onSuggest={setInput} />
          ) : (
            <div className="max-w-2xl mx-auto space-y-5">
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
        />
      </div>
    </div>
  );
}
