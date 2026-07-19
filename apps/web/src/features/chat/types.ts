import type { GenerationProvider } from '@/lib/api';

export type ChatMessageRole = 'user' | 'assistant';
export type ChatMessageStage = 'streaming' | 'done' | 'error';

export interface ChatMessage {
  id: string;
  role: ChatMessageRole;
  content: string;
  stage: ChatMessageStage;
  error?: string;
  createdAt: string;
}

export interface ChatConversation {
  /** `conversation_id` from the backend once the first turn completes. */
  conversationId: string;
  title: string;
  messages: ChatMessage[];
  updatedAt: string;
}

export interface ChatConversationSummary {
  conversationId: string;
  title: string;
  updatedAt: string;
}

export interface ChatSendOptions {
  provider?: GenerationProvider;
}
