import { getStoredToken } from './auth';
import { extractErrorMessage } from './errors';
import { parseSSEStream, type SSEEvent } from './sse';

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getStoredToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
  if (init?.headers) {
    Object.assign(headers, init.headers);
  }

  const res = await fetch(`${BASE}${path}`, { ...init, headers });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const msg = extractErrorMessage(body, `${res.status} ${res.statusText}`);
    const err = new Error(msg) as Error & { status: number };
    err.status = res.status;
    throw err;
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export interface UserProfile {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  avatar_url: string | null;
  provider: string;
  verified: boolean;
}

export type DocumentUploadStatus = 'pending' | 'uploading' | 'completed' | 'failed';
export type DocumentProcessingStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface Document {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  upload_status: DocumentUploadStatus;
  processing_status: DocumentProcessingStatus;
  storage_key: string;
  created_at: string;
  processing_error?: string | null;
}

export interface DocumentKnowledgeStats {
  indexed_chunk_count: number;
  embedding_count: number;
}

export interface GenerationUsageSummary {
  total_cost_usd: number;
  total_requests: number;
  total_tokens: number;
  month_cost_usd: number;
  month_requests: number;
  month_tokens: number;
  memory_extraction_cost_usd: number;
  memory_extraction_requests: number;
  answer_turns: number;
  memory_extraction_cost_per_100_turns: number;
}

export type InfrastructureServiceStatus = 'healthy' | 'unhealthy';

export interface HealthStatus {
  status: InfrastructureServiceStatus;
  services: {
    postgres: InfrastructureServiceStatus;
    valkey: InfrastructureServiceStatus;
    qdrant: InfrastructureServiceStatus;
  };
}

// Matches `app/ai/runtime/generation/enums.py::GenerationProvider`.
export type GenerationProvider = 'groq' | 'openai' | 'claude' | 'gemini' | 'ollama';

// Matches `app/ai/knowledge/context/citations/models.py::Citation`.
export interface Citation {
  citation_id: string;
  filename: string;
  document_id: string;
  page_numbers: number[];
  heading: string | null;
  heading_path: string[];
  chunk_ids: string[];
}

// Matches `app/ai/research/models.py::ResearchSource`.
export interface ResearchSource {
  document_id: string;
  filename: string;
  chunk_id: string;
  score: number;
  page: number | null;
}

// Matches `app/schemas/research.py::ResearchResponse`.
export interface ResearchResponse {
  research_id: string;
  conversation_id: string;
  query: string;
  answer: string;
  citations: Citation[];
  sources: ResearchSource[];
  duration_ms: number;
}

// Matches `app/schemas/research.py::ResearchSessionResponse` (GET /research/{id}).
export interface ResearchSessionResponse {
  research_id: string;
  conversation_id: string | null;
  query: string;
  answer: string;
  citations: Citation[];
  sources: ResearchSource[];
  created_at: string;
}

// Matches `app/schemas/research.py::ResearchConversationSummary`.
export interface ResearchConversationSummary {
  conversation_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

// Matches `app/schemas/research.py::ResearchConversationListResponse`.
export interface ResearchConversationListResponse {
  conversations: ResearchConversationSummary[];
}

// Matches `app/schemas/research.py::ResearchConversationResponse`.
export interface ResearchConversationResponse {
  conversation_id: string;
  title: string | null;
  turns: ResearchSessionResponse[];
}

// Matches `app/ai/runtime/events/models.py::StreamEvent`, as sent over SSE
// by both the Research and Chat runtimes (a shared canonical shape — see
// ADR-028's "Layer 2 — Canonical Stream Events").
export interface RuntimeStreamEvent {
  event_id: string;
  session_id: string | null;
  request_id: string | null;
  parent_event_id: string | null;
  category: 'generation' | 'research' | 'agent' | 'tool';
  type: string;
  timestamp: string;
  content: string | null;
  metadata: Record<string, unknown>;
}

// Alias kept for call sites that specifically mean "a research stream event".
export type ResearchStreamEvent = RuntimeStreamEvent;

export const PROVIDER_OPTIONS: { value: GenerationProvider | 'auto'; label: string }[] = [
  { value: 'auto', label: 'Auto' },
  { value: 'claude', label: 'Claude' },
  { value: 'openai', label: 'OpenAI' },
  { value: 'gemini', label: 'Gemini' },
  { value: 'groq', label: 'Groq' },
];

export interface ResearchAskOptions {
  topK?: number;
  filters?: Record<string, unknown>;
  provider?: GenerationProvider;
  conversationId?: string;
}

async function* streamResearch(
  query: string,
  options: ResearchAskOptions = {}
): AsyncGenerator<SSEEvent<ResearchStreamEvent>> {
  const token = getStoredToken();

  let res: Response;
  try {
    res = await fetch(`${BASE}/api/v1/research/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        query,
        top_k: options.topK ?? 10,
        filters: options.filters ?? {},
        provider: options.provider ?? null,
        conversation_id: options.conversationId ?? null,
      }),
    });
  } catch {
    throw new Error('Could not reach the server. Is the backend running?');
  }

  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(body, `Research stream failed (${res.status})`));
  }

  yield* parseSSEStream<ResearchStreamEvent>(res.body);
}

export interface ChatStreamOptions {
  conversationId?: string;
  provider?: GenerationProvider;
}

export interface ChatMessageResponse {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  provider: string | null;
  model: string | null;
  created_at: string;
}

export interface ChatConversationSummaryResponse {
  conversation_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChatConversationListResponse {
  conversations: ChatConversationSummaryResponse[];
  next_cursor: string | null;
}

export interface ChatConversationResponse {
  conversation_id: string;
  title: string | null;
  messages: ChatMessageResponse[];
  next_cursor: string | null;
}

// Matches `app/api/v1/chat.py`'s SSE streaming endpoint.
async function* streamChat(
  userPrompt: string,
  options: ChatStreamOptions = {}
): AsyncGenerator<SSEEvent<RuntimeStreamEvent>> {
  const token = getStoredToken();

  let res: Response;
  try {
    res = await fetch(`${BASE}/api/v1/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        user_prompt: userPrompt,
        conversation_id: options.conversationId ?? null,
        provider: options.provider ?? null,
      }),
    });
  } catch {
    throw new Error('Could not reach the server. Is the backend running?');
  }

  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(body, `Chat stream failed (${res.status})`));
  }

  yield* parseSSEStream<RuntimeStreamEvent>(res.body);
}

export const api = {
  auth: {
    me: () => request<UserProfile>('/api/v1/auth/me'),
  },
  health: {
    get: async () => {
      const response = await request<{ data: HealthStatus }>('/api/v1/health');
      return response.data;
    },
  },
  usage: {
    summary: () => request<GenerationUsageSummary>('/api/v1/usage/summary'),
  },
  chat: {
    stream: streamChat,
    listConversations: (cursor?: string) =>
      request<ChatConversationListResponse>(
        `/api/v1/chat/conversations${cursor ? `?cursor=${encodeURIComponent(cursor)}` : ''}`
      ),
    getConversation: (conversationId: string, cursor?: string) =>
      request<ChatConversationResponse>(
        `/api/v1/chat/conversations/${conversationId}${
          cursor ? `?cursor=${encodeURIComponent(cursor)}` : ''
        }`
      ),
  },
  research: {
    ask: (query: string, options: ResearchAskOptions = {}) =>
      request<ResearchResponse>('/api/v1/research', {
        method: 'POST',
        body: JSON.stringify({
          query,
          top_k: options.topK ?? 10,
          filters: options.filters ?? {},
          provider: options.provider ?? null,
          conversation_id: options.conversationId ?? null,
        }),
      }),
    stream: streamResearch,
    get: (researchId: string) =>
      request<ResearchSessionResponse>(`/api/v1/research/${researchId}`),
    listConversations: () =>
      request<ResearchConversationListResponse>('/api/v1/research/conversations'),
    getConversation: (conversationId: string) =>
      request<ResearchConversationResponse>(`/api/v1/research/conversations/${conversationId}`),
  },
  documents: {
    list: () => request<Document[]>('/api/v1/documents'),
    stats: () => request<DocumentKnowledgeStats>('/api/v1/documents/stats'),
    upload: async (file: File): Promise<Document> => {
      const token = getStoredToken();
      const form = new FormData();
      form.append('file', file);

      let res: Response;
      try {
        res = await fetch(`${BASE}/api/v1/documents/upload`, {
          method: 'POST',
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: form,
        });
      } catch {
        // fetch() itself threw: the connection never completed (server down,
        // crashed mid-response, or a dev-server hot-reload killed it).
        throw new Error('Could not reach the server. Is the backend running?');
      }

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(extractErrorMessage(body, `Upload failed (${res.status})`));
      }
      return res.json() as Promise<Document>;
    },
  },
};
