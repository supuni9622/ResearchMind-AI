'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '@/lib/api';
import type {
  ChatConversation,
  ChatConversationSummary,
  ChatMessage,
  ChatSendOptions,
} from '@/features/chat/types';

// There is no `GET /chat/conversations` or `GET /chat/{id}` endpoint yet --
// the Chat runtime (unlike Research) has no server-side history read path,
// only a write path (`ConversationService.append_turn`, persisted but never
// re-exposed over HTTP). So, unlike `useResearch`, the full transcript --
// not just an id + query -- has to live in localStorage for this browser to
// be able to redisplay a past conversation at all.
const STORE_KEY = 'rm_chat_conversations';
const STORE_LIMIT = 30;
const TITLE_LENGTH = 48;

function loadConversations(): ChatConversation[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(STORE_KEY);
    return raw ? (JSON.parse(raw) as ChatConversation[]) : [];
  } catch {
    return [];
  }
}

function saveConversations(conversations: ChatConversation[]): void {
  try {
    window.localStorage.setItem(STORE_KEY, JSON.stringify(conversations.slice(0, STORE_LIMIT)));
  } catch {}
}

function titleFrom(text: string): string {
  const trimmed = text.trim();
  return trimmed.length > TITLE_LENGTH ? `${trimmed.slice(0, TITLE_LENGTH)}…` : trimmed;
}

function patchMessage(
  messages: ChatMessage[],
  id: string,
  patch: Partial<ChatMessage> | ((m: ChatMessage) => Partial<ChatMessage>)
): ChatMessage[] {
  return messages.map((m) =>
    m.id === id ? { ...m, ...(typeof patch === 'function' ? patch(m) : patch) } : m
  );
}

export function useChat() {
  const [store, setStore] = useState<ChatConversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    setStore(loadConversations());
  }, []);

  const conversations: ChatConversationSummary[] = useMemo(
    () =>
      [...store]
        .sort((a, b) => (a.updatedAt < b.updatedAt ? 1 : -1))
        .map(({ conversationId, title, updatedAt }) => ({ conversationId, title, updatedAt })),
    [store]
  );

  const persist = useCallback((conversationId: string, patch: Partial<ChatConversation>) => {
    setStore((prev) => {
      const existing = prev.find((c) => c.conversationId === conversationId);
      const next: ChatConversation = existing
        ? { ...existing, ...patch }
        : {
            conversationId,
            title: '',
            messages: [],
            updatedAt: new Date().toISOString(),
            ...patch,
          };
      const rest = prev.filter((c) => c.conversationId !== conversationId);
      const updated = [next, ...rest];
      saveConversations(updated);
      return updated;
    });
  }, []);

  const send = useCallback(
    async (text: string, options: ChatSendOptions = {}) => {
      const query = text.trim();
      if (!query || sending) return;

      setSending(true);

      const userMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content: query,
        stage: 'done',
        createdAt: new Date().toISOString(),
      };
      const assistantId = crypto.randomUUID();
      const assistantMessage: ChatMessage = {
        id: assistantId,
        role: 'assistant',
        content: '',
        stage: 'streaming',
        createdAt: new Date().toISOString(),
      };

      const conversationIdAtStart = activeConversationId;
      setMessages((prev) => [...prev, userMessage, assistantMessage]);

      let resolvedConversationId: string | null = conversationIdAtStart;

      try {
        for await (const { data: event } of api.chat.stream(query, {
          conversationId: conversationIdAtStart ?? undefined,
          provider: options.provider,
        })) {
          if (event.session_id && !resolvedConversationId) {
            resolvedConversationId = event.session_id;
            setActiveConversationId(resolvedConversationId);
          }

          if (event.type === 'token' && event.content) {
            setMessages((prev) =>
              patchMessage(prev, assistantId, (m) => ({ content: m.content + event.content }))
            );
            continue;
          }

          if (event.type === 'error') {
            setMessages((prev) =>
              patchMessage(prev, assistantId, {
                stage: 'error',
                error: event.content ?? 'The assistant returned an error.',
              })
            );
            return;
          }
        }

        setMessages((prev) => {
          const finished = patchMessage(prev, assistantId, { stage: 'done' });
          if (resolvedConversationId) {
            persist(resolvedConversationId, {
              title: titleFrom(finished.find((m) => m.role === 'user')?.content ?? query) || 'New chat',
              messages: finished,
              updatedAt: new Date().toISOString(),
            });
          }
          return finished;
        });
      } catch (err) {
        setMessages((prev) =>
          patchMessage(prev, assistantId, {
            stage: 'error',
            error: err instanceof Error ? err.message : 'Something went wrong.',
          })
        );
      } finally {
        setSending(false);
      }
    },
    [activeConversationId, sending, persist]
  );

  const selectConversation = useCallback(
    (conversationId: string) => {
      const conversation = store.find((c) => c.conversationId === conversationId);
      if (!conversation) return;
      setActiveConversationId(conversationId);
      setMessages(conversation.messages);
    },
    [store]
  );

  const newConversation = useCallback(() => {
    setActiveConversationId(null);
    setMessages([]);
  }, []);

  const deleteConversation = useCallback(
    (conversationId: string) => {
      setStore((prev) => {
        const updated = prev.filter((c) => c.conversationId !== conversationId);
        saveConversations(updated);
        return updated;
      });
      if (activeConversationId === conversationId) {
        setActiveConversationId(null);
        setMessages([]);
      }
    },
    [activeConversationId]
  );

  return {
    conversations,
    activeConversationId,
    messages,
    sending,
    send,
    selectConversation,
    newConversation,
    deleteConversation,
  };
}
