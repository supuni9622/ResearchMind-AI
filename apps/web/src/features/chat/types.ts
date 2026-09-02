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

// Wave 4 chat attachments (docs/PRIORITIZED_ROADMAP.md) -- an image
// uploaded via POST /chat/attachments ahead of the turn, referenced by id
// in the ChatStreamRequest that follows.
export interface ChatAttachment {
  id: string;
  filename: string;
  contentType: string;
  url: string;
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
  /** From the stream's `generation_id` metadata (E21) -- present once the
   * first event carrying it has arrived; required to submit feedback.
   * Absent for messages loaded from conversation history (the backend
   * doesn't return it on GET /chat/{id} yet), not just mid-stream. */
  generationId?: string;
  memoryUsed?: boolean;
  attachments?: ChatAttachment[];
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
  /** Already-uploaded (via `api.chat.uploadAttachment`) images for this
   * turn -- full metadata, not just ids, so the just-sent user bubble can
   * render thumbnails immediately without waiting for a reload. */
  attachments?: ChatAttachment[];
}
