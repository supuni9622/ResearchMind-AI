'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '@/lib/api';
import { getStoredToken } from '@/lib/auth';
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

// Must match apps/api/app/core/settings.py's `deepgram_sample_rate`
// default -- there is no runtime negotiation of this value between
// client and server.
const VOICE_TARGET_SAMPLE_RATE = 16000;

export type VoiceChatStatus = 'idle' | 'connecting' | 'listening' | 'speaking' | 'error';

function voiceWebSocketUrl(): string {
  const base = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
  return base.replace(/^http/, 'ws') + '/api/v1/chat/voice';
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

  // -------------------------------------------------------------------
  // Voice (docs/todo/voice-chat-poc-implementation-plan.md T13). Kept in
  // this hook, not a separate one, specifically so it can reuse
  // `messages`/`setMessages`/`patchMessage`/`activeConversationId` and
  // therefore the existing `MessageBubble` rendering, instead of
  // maintaining a second, parallel message list.
  // -------------------------------------------------------------------
  const [voiceStatus, setVoiceStatus] = useState<VoiceChatStatus>('idle');
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const [voiceDraftTranscript, setVoiceDraftTranscript] = useState('');

  const voiceWsRef = useRef<WebSocket | null>(null);
  const voiceAudioContextRef = useRef<AudioContext | null>(null);
  const voiceMicStreamRef = useRef<MediaStream | null>(null);
  const voiceWorkletNodeRef = useRef<AudioWorkletNode | null>(null);
  const voicePlayerRef = useRef<HTMLAudioElement | null>(null);
  const voiceMediaSourceRef = useRef<MediaSource | null>(null);
  const voiceSourceBufferRef = useRef<SourceBuffer | null>(null);
  const voicePendingAudioRef = useRef<ArrayBuffer[]>([]);
  const voiceAssistantIdRef = useRef<string | null>(null);

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
          if (event.metadata?.memory_used === true) {
            setMessages((prev) => patchMessage(prev, assistantId, { memoryUsed: true }));
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

        setMessages((prev) => patchMessage(prev, assistantId, { stage: 'done' }));
        if (resolvedConversationId) {
          // Title generation is awaited by the stream's persistence tail, so
          // refresh only after the iterator closes. Keep this side effect out
          // of the React state updater, which may run more than once in dev.
          try {
            await refreshConversations();
          } catch {
            // The answer is already complete; a sidebar refresh failure must
            // not turn the successful assistant message into an error.
          }
        }
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

  const stopVoiceChat = useCallback(() => {
    voiceWorkletNodeRef.current?.disconnect();
    voiceWorkletNodeRef.current = null;
    voiceMicStreamRef.current?.getTracks().forEach((track) => track.stop());
    voiceMicStreamRef.current = null;
    if (voiceAudioContextRef.current) {
      void voiceAudioContextRef.current.close().catch(() => {});
      voiceAudioContextRef.current = null;
    }
    voiceWsRef.current?.close(1000, 'user stopped voice');
    voiceWsRef.current = null;
    if (voicePlayerRef.current) {
      voicePlayerRef.current.pause();
      URL.revokeObjectURL(voicePlayerRef.current.src);
    }
    voicePlayerRef.current = null;
    voiceMediaSourceRef.current = null;
    voiceSourceBufferRef.current = null;
    voicePendingAudioRef.current = [];
    voiceAssistantIdRef.current = null;
    setVoiceStatus('idle');
    setVoiceDraftTranscript('');
  }, []);

  // Voice counterpart to `send()` above (docs/todo/
  // voice-chat-poc-implementation-plan.md T13). Deliberately not
  // reusing `send()` itself -- that function is a single SSE fetch per
  // turn; this opens one long-lived WebSocket that carries *every* turn
  // of a voice session, so the per-turn bookkeeping (`patchMessage`
  // calls, completion/error handling) is structurally similar but the
  // connection lifecycle is not. Untested in a real browser -- see the
  // plan doc's T13/T14 notes.
  const startVoiceChat = useCallback(
    async (options: ChatSendOptions = {}) => {
      if (voiceStatus === 'connecting' || voiceStatus === 'listening' || voiceStatus === 'speaking') {
        return;
      }

      const token = getStoredToken();
      if (!token) {
        setVoiceError('Not signed in.');
        setVoiceStatus('error');
        return;
      }

      setVoiceError(null);
      setVoiceStatus('connecting');

      let resolvedConversationId = activeConversationId;
      const conversationIdAtStart = activeConversationId;

      const flushPendingAudio = () => {
        const sourceBuffer = voiceSourceBufferRef.current;
        if (!sourceBuffer || sourceBuffer.updating || voicePendingAudioRef.current.length === 0) {
          return;
        }
        const chunk = voicePendingAudioRef.current.shift();
        if (!chunk) return;
        try {
          sourceBuffer.appendBuffer(chunk);
        } catch (err) {
          // `QuotaExceededError` if the buffer somehow still fills up
          // despite the per-turn reset below (e.g. an unusually long
          // response). Dropping the rest of this turn's audio is a much
          // better failure mode than leaving the whole pipeline wedged --
          // text has already rendered by this point regardless.
          console.warn('voice playback: appendBuffer failed, dropping remaining audio for this turn', err);
          voicePendingAudioRef.current = [];
        }
      };

      // Playback: MediaSource + a detached <audio> element, not manual
      // PCM scheduling -- ElevenLabs' free-tier output format is MP3,
      // not a PCM format that could be scheduled manually (confirmed via
      // their docs; PCM output requires a paid tier). Same choice as
      // tools/voice-test-page/index.html, for the same reason.
      //
      // A fresh `MediaSource`/`SourceBuffer` per *turn*, not one reused
      // for the whole voice session: a `SourceBuffer` has a finite quota,
      // and nothing here ever plays fast enough to evict old data on its
      // own across a long multi-turn conversation -- confirmed live
      // (2026-08-27): a single long response filled the buffer and
      // `appendBuffer` threw, silently killing audio for the rest of the
      // session. Resetting per turn keeps each `SourceBuffer`'s lifetime
      // bounded to one response.
      const setupVoicePlayback = () => {
        const previousPlayer = voicePlayerRef.current;
        if (previousPlayer) {
          previousPlayer.pause();
          URL.revokeObjectURL(previousPlayer.src);
        }
        voiceSourceBufferRef.current = null;
        voicePendingAudioRef.current = [];

        const player = new Audio();
        const mediaSource = new MediaSource();
        player.src = URL.createObjectURL(mediaSource);
        voicePlayerRef.current = player;
        voiceMediaSourceRef.current = mediaSource;

        mediaSource.addEventListener(
          'sourceopen',
          () => {
            const sourceBuffer = mediaSource.addSourceBuffer('audio/mpeg');
            sourceBuffer.addEventListener('updateend', flushPendingAudio);
            voiceSourceBufferRef.current = sourceBuffer;
            flushPendingAudio(); // in case audio already arrived before sourceopen fired
          },
          { once: true }
        );

        // Explicit `.play()`, not just the `autoplay` attribute, so a
        // rejected promise (e.g. the browser's autoplay policy) surfaces
        // as a real error instead of failing silently.
        player.play().catch((err) => {
          console.warn('voice playback: play() was rejected', err);
        });
      };

      const ws = new WebSocket(`${voiceWebSocketUrl()}?token=${encodeURIComponent(token)}`);
      ws.binaryType = 'arraybuffer';
      voiceWsRef.current = ws;

      ws.onopen = () => {
        ws.send(
          JSON.stringify({
            conversation_id: conversationIdAtStart,
            provider: options.provider ?? null,
            web_search_enabled: options.webSearchEnabled ?? false,
            paper_search_enabled: options.paperSearchEnabled ?? false,
          })
        );
        setVoiceStatus('listening');
      };

      ws.onmessage = (event) => {
        if (event.data instanceof ArrayBuffer) {
          voicePendingAudioRef.current.push(event.data);
          flushPendingAudio();
          setVoiceStatus('speaking');
          return;
        }

        let payload: Record<string, unknown>;
        try {
          payload = JSON.parse(event.data as string);
        } catch {
          return;
        }

        if (typeof payload.session_id === 'string' && !resolvedConversationId) {
          resolvedConversationId = payload.session_id;
          setActiveConversationId(resolvedConversationId);
          onConversationCreated?.(resolvedConversationId);
        }

        if (payload.type === 'voice.transcript') {
          const transcript = typeof payload.transcript === 'string' ? payload.transcript : '';
          if (payload.is_final) {
            setVoiceDraftTranscript('');
            setupVoicePlayback(); // fresh SourceBuffer for this turn's response

            const userMessage: ChatMessage = {
              id: crypto.randomUUID(),
              role: 'user',
              content: transcript,
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
            voiceAssistantIdRef.current = assistantId;
            setMessages((prev) => [...prev, userMessage, assistantMessage]);
          } else {
            setVoiceDraftTranscript(transcript);
          }
          return;
        }

        if (payload.type === 'voice.interrupted') {
          setVoiceStatus('listening');
          voicePendingAudioRef.current = [];
          try {
            const sourceBuffer = voiceSourceBufferRef.current;
            if (sourceBuffer && !sourceBuffer.updating) sourceBuffer.abort();
          } catch {
            // Best-effort stop -- see tools/voice-test-page/index.html's
            // identical note on why MSE has no atomic "go silent now".
          }
          voicePlayerRef.current?.pause();

          // The server aborts generation entirely on interrupt (see
          // response_stream.py) -- without this, the in-progress
          // assistant message is left at `stage: 'streaming'` forever
          // (an infinite typing indicator, confirmed live 2026-08-27).
          // If no content ever arrived, this reads as a real error (it
          // functionally is one from the user's perspective: they got no
          // answer); if some did, keep it and mark it done rather than
          // discarding a partial answer.
          const interruptedId = voiceAssistantIdRef.current;
          if (interruptedId) {
            setMessages((prev) =>
              patchMessage(prev, interruptedId, (m) =>
                m.content
                  ? { stage: 'done' }
                  : { stage: 'error', error: 'Interrupted before a response arrived.' }
              )
            );
            voiceAssistantIdRef.current = null;
          }
          return;
        }

        const assistantId = voiceAssistantIdRef.current;
        if (!assistantId) return;

        if (!resolvedConversationId && typeof payload.metadata === 'object' && payload.metadata) {
          const generationId = (payload.metadata as Record<string, unknown>).generation_id;
          if (typeof generationId === 'string') {
            setMessages((prev) => patchMessage(prev, assistantId, { generationId }));
          }
        }
        if (
          typeof payload.metadata === 'object' &&
          payload.metadata &&
          (payload.metadata as Record<string, unknown>).memory_used === true
        ) {
          setMessages((prev) => patchMessage(prev, assistantId, { memoryUsed: true }));
        }

        if (payload.type === 'token' && typeof payload.content === 'string') {
          const tokenContent = payload.content;
          setMessages((prev) =>
            patchMessage(prev, assistantId, (m) => ({ content: m.content + tokenContent }))
          );
          return;
        }

        if (payload.type === 'complete' || payload.type === 'completed') {
          setMessages((prev) => patchMessage(prev, assistantId, { stage: 'done' }));
          setVoiceStatus('listening');
          voiceAssistantIdRef.current = null;
          if (resolvedConversationId) {
            void refreshConversations().catch(() => {
              // Same rationale as `send()`: a sidebar refresh failure
              // must not turn a successful turn into an error.
            });
          }
          return;
        }

        if (payload.type === 'error') {
          const errorContent =
            typeof payload.content === 'string' ? payload.content : 'The assistant returned an error.';
          setMessages((prev) => patchMessage(prev, assistantId, { stage: 'error', error: errorContent }));
          setVoiceStatus('listening');
          voiceAssistantIdRef.current = null;
        }
      };

      ws.onerror = () => {
        setVoiceError('Voice connection error.');
      };

      ws.onclose = () => {
        setVoiceStatus((current) => (current === 'error' ? current : 'idle'));
      };

      // Mic capture via AudioWorklet -- not the deprecated
      // ScriptProcessorNode tools/voice-test-page/index.html uses for
      // single-file simplicity; this is real product code.
      try {
        const micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const audioContext = new AudioContext();
        await audioContext.audioWorklet.addModule('/voice-worklet.js');
        const micSource = audioContext.createMediaStreamSource(micStream);
        const workletNode = new AudioWorkletNode(audioContext, 'voice-downsample-processor', {
          processorOptions: { targetSampleRate: VOICE_TARGET_SAMPLE_RATE },
        });
        workletNode.port.onmessage = (workletEvent: MessageEvent<ArrayBuffer>) => {
          if (ws.readyState === WebSocket.OPEN) ws.send(workletEvent.data);
        };
        micSource.connect(workletNode);

        voiceMicStreamRef.current = micStream;
        voiceAudioContextRef.current = audioContext;
        voiceWorkletNodeRef.current = workletNode;
      } catch (err) {
        setVoiceError(err instanceof Error ? err.message : 'Microphone access failed.');
        setVoiceStatus('error');
        ws.close();
      }
    },
    [activeConversationId, voiceStatus, onConversationCreated, refreshConversations]
  );

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
    voiceStatus,
    voiceError,
    voiceDraftTranscript,
    startVoiceChat,
    stopVoiceChat,
  };
}
