import type { GenerationProvider } from '@/lib/api';

export type ChatMessageRole = 'user' | 'assistant';
export type ChatMessageStage = 'streaming' | 'done' | 'error';

// Mirrors `ChatEventType` (chat_web_search_started/completed/skipped) --
// absent means the toggle was off or the agent decided it didn't need the
// web for this turn, so no chip renders (web_search_tool_platform_prd.md).
export type ChatWebSearchStage = 'searching' | 'done' | 'skipped';

export interface ChatWebSource {
  title: string;
  url: string;
  domain: string;
}

export interface ChatWebSearchStatus {
  stage: ChatWebSearchStage;
  query?: string;
  sources?: ChatWebSource[];
}

// Mirrors `ChatEventType` (chat_paper_search_started/completed/skipped) --
// absent means the toggle was off or the search returned nothing usable.
export type ChatPaperSearchStage = 'searching' | 'done' | 'skipped';

export interface ChatPaperSource {
  title: string;
  authors: string[];
  year: number | null;
  url: string | null;
}

export interface ChatPaperSearchStatus {
  stage: ChatPaperSearchStage;
  sources?: ChatPaperSource[];
}

export interface ChatMessage {
  id: string;
  role: ChatMessageRole;
  content: string;
  stage: ChatMessageStage;
  error?: string;
  createdAt: string;
  webSearch?: ChatWebSearchStatus;
  paperSearch?: ChatPaperSearchStatus;
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
  webSearchEnabled?: boolean;
  paperSearchEnabled?: boolean;
}
