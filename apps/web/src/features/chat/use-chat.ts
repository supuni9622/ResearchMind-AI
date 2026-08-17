'use client';

import { useCallback, useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type {
  ChatConversationSummary,
  ChatMessage,
  ChatPaperSource,
  ChatSendOptions,
  ChatWebSource,
} from '@/features/chat/types';

function patchMessage(
  messages: ChatMessage[],
  id: string,
  patch: Partial<ChatMessage> | ((m: ChatMessage) => Partial<ChatMessage>)
): ChatMessage[] {
  return messages.map((m) =>
    m.id === id ? { ...m, ...(typeof patch === 'function' ? patch(m) : patch) } : m
  );
}

export function useChat({
  onConversationCreated,
}: {
  onConversationCreated?: (conversationId: string) => void;
} = {}) {
  const [conversations, setConversations] = useState<ChatConversationSummary[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sending, setSending] = useState(false);
  const [conversationCursor, setConversationCursor] = useState<string | null>(null);
  const [messageCursor, setMessageCursor] = useState<string | null>(null);
  const [loadingOlderMessages, setLoadingOlderMessages] = useState(false);
  const [loadingMoreConversations, setLoadingMoreConversations] = useState(false);

  useEffect(() => {
    void api.chat
      .listConversations()
      .then(({ conversations: items, next_cursor }) => {
        setConversations(
          items.map((conversation) => ({
            conversationId: conversation.conversation_id,
            title: conversation.title ?? 'New chat',
            updatedAt: conversation.updated_at,
          }))
        );
        setConversationCursor(next_cursor);
      })
      .catch(() => {
        setConversations([]);
        setConversationCursor(null);
      });
  }, []);

  const refreshConversations = useCallback(async () => {
    const { conversations: items, next_cursor } = await api.chat.listConversations();
    setConversations(
      items.map((conversation) => ({
        conversationId: conversation.conversation_id,
        title: conversation.title ?? 'New chat',
        updatedAt: conversation.updated_at,
      }))
    );
    setConversationCursor(next_cursor);
  }, []);

  const loadMoreConversations = useCallback(async () => {
    if (!conversationCursor || loadingMoreConversations) return;
    setLoadingMoreConversations(true);
    try {
      const { conversations: items, next_cursor } = await api.chat.listConversations(
        conversationCursor
      );
      setConversations((current) => {
        const seen = new Set(current.map((conversation) => conversation.conversationId));
        return [
          ...current,
          ...items
            .filter((conversation) => !seen.has(conversation.conversation_id))
            .map((conversation) => ({
              conversationId: conversation.conversation_id,
              title: conversation.title ?? 'New chat',
              updatedAt: conversation.updated_at,
            })),
        ];
      });
      setConversationCursor(next_cursor);
    } finally {
      setLoadingMoreConversations(false);
    }
  }, [conversationCursor, loadingMoreConversations]);

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
      let resolvedGenerationId: string | null = null;

      try {
        for await (const { data: event } of api.chat.stream(query, {
          conversationId: conversationIdAtStart ?? undefined,
          provider: options.provider,
          webSearchEnabled: options.webSearchEnabled,
          paperSearchEnabled: options.paperSearchEnabled,
        })) {
          if (event.session_id && !resolvedConversationId) {
            resolvedConversationId = event.session_id;
            setActiveConversationId(resolvedConversationId);
            onConversationCreated?.(resolvedConversationId);
          }

          // Stamped on every event by StreamingService (E21) -- captured
          // once, from whichever event happens to arrive first with it.
          if (!resolvedGenerationId && typeof event.metadata?.generation_id === 'string') {
            resolvedGenerationId = event.metadata.generation_id;
            setMessages((prev) =>
              patchMessage(prev, assistantId, { generationId: resolvedGenerationId! })
            );
          }

          if (event.type === 'chat_web_search_started') {
            const query = event.metadata?.query;
            setMessages((prev) =>
              patchMessage(prev, assistantId, {
                webSearch: {
                  stage: 'searching',
                  query: typeof query === 'string' ? query : undefined,
                },
              })
            );
            continue;
          }

          if (event.type === 'chat_web_search_completed') {
            const sources = Array.isArray(event.metadata?.sources)
              ? (event.metadata.sources as ChatWebSource[])
              : [];
            setMessages((prev) =>
              patchMessage(prev, assistantId, (m) => ({
                webSearch: { stage: 'done', query: m.webSearch?.query, sources },
              }))
            );
            continue;
          }

          if (event.type === 'chat_web_search_skipped') {
            setMessages((prev) =>
              patchMessage(prev, assistantId, (m) => ({
                webSearch: { stage: 'skipped', query: m.webSearch?.query },
              }))
            );
            continue;
          }

          if (event.type === 'chat_paper_search_started') {
            setMessages((prev) =>
              patchMessage(prev, assistantId, { paperSearch: { stage: 'searching' } })
            );
            continue;
          }

          if (event.type === 'chat_paper_search_completed') {
            const sources = Array.isArray(event.metadata?.sources)
              ? (event.metadata.sources as ChatPaperSource[])
              : [];
            setMessages((prev) =>
              patchMessage(prev, assistantId, { paperSearch: { stage: 'done', sources } })
            );
            continue;
          }

          if (event.type === 'chat_paper_search_skipped') {
            setMessages((prev) =>
              patchMessage(prev, assistantId, { paperSearch: { stage: 'skipped' } })
            );
            continue;
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
            void refreshConversations();
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
    [activeConversationId, sending, refreshConversations, onConversationCreated]
  );

  const selectConversation = useCallback(
    async (conversationId: string) => {
      const conversation = await api.chat.getConversation(conversationId);
      setActiveConversationId(conversationId);
      setMessages(
        conversation.messages.map((message) => ({
          id: message.id,
          role: message.role,
          content: message.content,
          stage: 'done',
          createdAt: message.created_at,
        }))
      );
      setMessageCursor(conversation.next_cursor);
    },
    []
  );

  const loadOlderMessages = useCallback(async () => {
    if (!activeConversationId || !messageCursor || loadingOlderMessages) return;
    setLoadingOlderMessages(true);
    try {
      const conversation = await api.chat.getConversation(activeConversationId, messageCursor);
      setMessages((current) => [
        ...conversation.messages.map((message) => ({
          id: message.id,
          role: message.role,
          content: message.content,
          stage: 'done' as const,
          createdAt: message.created_at,
        })),
        ...current,
      ]);
      setMessageCursor(conversation.next_cursor);
    } finally {
      setLoadingOlderMessages(false);
    }
  }, [activeConversationId, loadingOlderMessages, messageCursor]);

  const newConversation = useCallback(() => {
    setActiveConversationId(null);
    setMessages([]);
    setMessageCursor(null);
  }, []);

  return {
    conversations,
    activeConversationId,
    messages,
    sending,
    hasMoreConversations: conversationCursor !== null,
    hasOlderMessages: messageCursor !== null,
    loadingMoreConversations,
    loadingOlderMessages,
    send,
    selectConversation,
    newConversation,
    loadMoreConversations,
    loadOlderMessages,
  };
}
