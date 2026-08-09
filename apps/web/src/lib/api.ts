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

export type DocumentKind = 'pdf' | 'docx' | 'markdown' | 'other';

export interface DocumentListParams {
  limit?: number;
  offset?: number;
  search?: string;
  kind?: DocumentKind;
}

export interface DocumentListResponse {
  items: Document[];
  total: number;
  limit: number;
  offset: number;
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

export interface GenerationProvidersResponse {
  providers: GenerationProvider[];
}

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
  deep_research_runs: DeepResearchTurnResponse[];
}

// Matches `app/schemas/generation_usage.py::ConversationUsageSummary`
// (GET /research/conversations/{id}/cost). Linear Research turns only --
// Deep Research runs are billed per-run under `session_id`, not
// `conversation_id`, so they're excluded from this rollup.
export interface ConversationUsageSummary {
  conversation_id: string;
  total_cost_usd: number;
  total_requests: number;
  total_tokens: number;
}

// Matches `app/schemas/research.py::ResearchReportDownloadResponse`.
export interface ResearchReportDownloadResponse {
  research_run_id: string;
  download_url: string;
  expires_in_seconds: number;
}

// Matches `app/ai/runtime/research/planner/models.py::ResearchComplexity`.
export type ResearchComplexity = 'simple' | 'moderate' | 'complex';

// Matches `app/ai/runtime/research/planner/models.py::ResearchPlanTask`.
export interface DeepResearchPlanTask {
  task_id: string;
  question: string;
  dependencies: string[];
  priority: number;
}

// Matches `app/ai/runtime/research/planner/models.py::ResearchPlan`.
export interface DeepResearchPlan {
  schema_version: number;
  goal: string;
  rewritten_goal: string | null;
  complexity: ResearchComplexity;
  execution_strategy: 'focused' | 'decomposed';
  tasks: DeepResearchPlanTask[];
  approval_required: boolean;
  clarification_question: string | null;
  limitations: string[];
}

// Matches `app/schemas/research.py::ResearchProposalResponse`.
export interface DeepResearchProposal {
  proposal_id: string;
  status: 'proposing' | 'awaiting_approval' | 'approved' | 'cancelled';
  conversation_id: string | null;
  /** The user's literal original question (distinct from `plan.goal`, the planner's own restatement). */
  query: string;
  plan: DeepResearchPlan;
  created_at: string;
}

// Matches `app/schemas/research.py::ResearchEscalationCheckResponse`.
export interface ResearchEscalationCheck {
  suggested: boolean;
  complexity: ResearchComplexity;
  reason: string;
  proposal: DeepResearchProposal | null;
}

// Matches `app/ai/runtime/research/types.py::ResearchRunStatus`.
export type DeepResearchRunStatus =
  | 'created'
  | 'planning'
  | 'researching'
  | 'reviewing'
  | 'synthesizing'
  | 'paused'
  | 'awaiting_approval'
  | 'awaiting_plan_approval'
  | 'awaiting_web_search_approval'
  | 'completed'
  | 'completed_with_limitations'
  | 'cancelled'
  | 'failed';

// Matches `app/schemas/research.py::ResearchRunResponse`.
export interface DeepResearchRun {
  research_run_id: string;
  status: DeepResearchRunStatus;
  current_phase: string | null;
  attempt_count: number;
  cancellation_requested: boolean;
  research_id: string | null;
  conversation_id: string | null;
  started_at: string | null;
  completed_at: string | null;
  /** e.g. `"report_rejected_returned_as_answer"` -- see `_complete_run` in `app/ai/runtime/research/execution.py`. */
  terminal_reason: string | null;
}

// Matches `app/schemas/research.py::DeepResearchTurnResponse`.
export interface DeepResearchTurnResponse {
  proposal: DeepResearchProposal;
  run: DeepResearchRun;
}

// Matches `app/schemas/research.py::ResearchDraftFindingResponse`.
export interface DeepResearchDraftFinding {
  heading: string;
  content: string;
  citation_ids: string[];
}

// Matches `app/schemas/research.py::ResearchDraftCitationResponse`.
export interface DeepResearchDraftCitation {
  citation_id: string;
  filename: string;
  excerpt: string;
  score: number;
}

// Matches `app/schemas/research.py::ResearchDraftReviewSummary`.
export interface DeepResearchDraftReview {
  decision: string;
  citation_integrity_score: number;
  completeness_score: number;
  limitations: string[];
}

// Matches `app/schemas/research.py::ResearchDraftResponse`.
export interface DeepResearchDraft {
  research_run_id: string;
  title: string;
  abstract: string;
  methodology: string;
  findings: DeepResearchDraftFinding[];
  discussion: string;
  conclusion: string;
  limitations: string[];
  citations: DeepResearchDraftCitation[];
  review: DeepResearchDraftReview;
}

/** Free-text edits submitted alongside approval -- matches
 * `app/schemas/research.py::ResearchDraftEdit`. Citation ids/schema
 * version/limitations aren't editable, so an edit can never break citation
 * integrity (see `ResearchRunService.record_report_decision`). */
export interface DeepResearchDraftEdit {
  title: string;
  abstract: string;
  methodology: string;
  findings: { heading: string; content: string }[];
  discussion: string;
  conclusion: string;
}

// Matches `app/schemas/research.py::ResearchPendingPlanTaskResponse`.
export interface DeepResearchPendingPlanTask {
  task_id: string;
  question: string;
}

// Matches `app/schemas/research.py::ResearchPendingPlanEvidenceSummary`.
export interface DeepResearchPendingPlanEvidence {
  completed_task_count: number;
  failed_task_count: number;
  warning_count: number;
}

// Matches `app/schemas/research.py::ResearchPendingPlanResponse` -- the plan
// and the evidence already gathered for it, read from the paused run's
// checkpoint while it's `awaiting_plan_approval` (reached after retrieval,
// before the synthesis call is spent).
export interface DeepResearchPendingPlan {
  research_run_id: string;
  goal: string;
  rewritten_goal: string | null;
  complexity: ResearchComplexity;
  tasks: DeepResearchPendingPlanTask[];
  evidence: DeepResearchPendingPlanEvidence;
  citations: DeepResearchDraftCitation[];
}

// Matches `app/schemas/research.py::ResearchPendingWebSearchResponse` -- the
// agent's web-search suggestion, read from the paused run's checkpoint while
// it's `awaiting_web_search_approval` (only reached in AUTO mode without
// `webSearchAutoApprove`).
export interface DeepResearchPendingWebSearch {
  research_run_id: string;
  suggested_query: string;
  reason: string;
  gap_question: string | null;
}

// Matches `app/schemas/research.py::WebSearchMode`.
export type DeepResearchWebSearchMode = 'disabled' | 'auto' | 'required';

export interface DeepResearchAskOptions {
  topK?: number;
  filters?: Record<string, unknown>;
  provider?: GenerationProvider;
  conversationId?: string;
  webSearchMode?: DeepResearchWebSearchMode;
  /** Skip the web-search approval pause: when AUTO decides a search would
   * help, proceed without asking. Ignored for DISABLED/REQUIRED. */
  webSearchAutoApprove?: boolean;
  includeDomains?: string[];
  excludeDomains?: string[];
  /** Opt-in, non-blocking: suggest related papers via the Research
   * Intelligence MCP server after the report is persisted -- never gates
   * the run (prds/3. mcp_server_setup.md). */
  paperSuggestionsEnabled?: boolean;
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

export const PROVIDER_LABELS: Record<GenerationProvider, string> = {
  claude: 'Claude',
  openai: 'OpenAI',
  gemini: 'Gemini',
  groq: 'Groq',
  ollama: 'Ollama (Local)',
};

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

// Matches `app/api/v1/research.py`'s `GET /research/runs/{id}/events` --
// durable, cursor-replayable progress events for one Deep Research run
// (planning/retrieval/synthesis/review/report milestones, plus the
// report-approval pause/resume). `after` resumes from a given event
// cursor rather than replaying from the start -- used both for the
// initial connection (`after=0`) and for reconnecting after a dropped
// stream (`after=<last seen cursor>`).
async function* streamResearchRunEvents(
  runId: string,
  after: number = 0,
  signal?: AbortSignal
): AsyncGenerator<SSEEvent<RuntimeStreamEvent>> {
  const token = getStoredToken();

  let res: Response;
  try {
    res = await fetch(`${BASE}/api/v1/research/runs/${runId}/events?after=${after}`, {
      headers: {
        Accept: 'text/event-stream',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      signal,
    });
  } catch (err) {
    if (signal?.aborted) throw err;
    throw new Error('Could not reach the server. Is the backend running?');
  }

  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(body, `Research run events stream failed (${res.status})`));
  }

  yield* parseSSEStream<RuntimeStreamEvent>(res.body);
}

export interface ChatStreamOptions {
  conversationId?: string;
  provider?: GenerationProvider;
  /** Pre-authorizes web search for this turn -- no approval pause in Chat,
   * enabling this toggle *is* the approval (web_search_tool_platform_prd.md). */
  webSearchEnabled?: boolean;
  /** Same toggle-is-the-approval shape, against the Research Intelligence
   * MCP server instead of Tavily (prds/3. mcp_server_setup.md). */
  paperSearchEnabled?: boolean;
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
        web_search_enabled: options.webSearchEnabled ?? false,
        paper_search_enabled: options.paperSearchEnabled ?? false,
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
  generation: {
    providers: async () => {
      const response = await request<{ data: GenerationProvidersResponse }>(
        '/api/v1/generation/providers'
      );
      return response.data.providers;
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
    getConversationCost: (conversationId: string) =>
      request<ConversationUsageSummary>(`/api/v1/research/conversations/${conversationId}/cost`),
    // Deep Research (research_runtime_prd.md) -- explicit-consent escalation
    // from Linear Research, or a manual mode selection. See
    // RESEARCH_RUNTIME_IMPLEMENTATION_TRACKER.md's "Chat-to-Research
    // escalation" item (this backs the Research-interface equivalent).
    checkEscalation: (query: string, options: DeepResearchAskOptions = {}) =>
      request<ResearchEscalationCheck>('/api/v1/research/escalation-check', {
        method: 'POST',
        body: JSON.stringify({
          query,
          top_k: options.topK ?? 10,
          filters: options.filters ?? {},
          provider: options.provider ?? null,
          conversation_id: options.conversationId ?? null,
        }),
      }),
    createProposal: (query: string, options: DeepResearchAskOptions = {}) =>
      request<DeepResearchProposal>('/api/v1/research/proposals', {
        method: 'POST',
        body: JSON.stringify({
          query,
          top_k: options.topK ?? 10,
          filters: options.filters ?? {},
          provider: options.provider ?? null,
          conversation_id: options.conversationId ?? null,
          web_search_mode: options.webSearchMode ?? 'disabled',
          web_search_auto_approve: options.webSearchAutoApprove ?? false,
          include_domains: options.includeDomains ?? [],
          exclude_domains: options.excludeDomains ?? [],
          paper_suggestions_enabled: options.paperSuggestionsEnabled ?? false,
        }),
      }),
    approveProposal: (proposalId: string) =>
      request<DeepResearchRun>(`/api/v1/research/proposals/${proposalId}/approve`, {
        method: 'POST',
      }),
    getRun: (runId: string) => request<DeepResearchRun>(`/api/v1/research/runs/${runId}`),
    cancelRun: (runId: string) =>
      request<DeepResearchRun>(`/api/v1/research/runs/${runId}/cancel`, { method: 'POST' }),
    submitReportDecision: (
      runId: string,
      approved: boolean,
      reason?: string,
      editedDraft?: DeepResearchDraftEdit
    ) =>
      request<DeepResearchRun>(`/api/v1/research/runs/${runId}/report-decision`, {
        method: 'POST',
        body: JSON.stringify({
          approved,
          reason: reason ?? null,
          edited_draft: editedDraft ?? null,
        }),
      }),
    getDraft: (runId: string) =>
      request<DeepResearchDraft>(`/api/v1/research/runs/${runId}/draft`),
    getPlan: (runId: string) =>
      request<DeepResearchPendingPlan>(`/api/v1/research/runs/${runId}/plan`),
    submitPlanDecision: (runId: string, approved: boolean, reason?: string, editedGoal?: string) =>
      request<DeepResearchRun>(`/api/v1/research/runs/${runId}/plan-decision`, {
        method: 'POST',
        body: JSON.stringify({
          approved,
          reason: reason ?? null,
          edited_plan: editedGoal ? { rewritten_goal: editedGoal } : null,
        }),
      }),
    getReportDownload: (runId: string) =>
      request<ResearchReportDownloadResponse>(`/api/v1/research/runs/${runId}/report`),
    getWebSearch: (runId: string) =>
      request<DeepResearchPendingWebSearch>(`/api/v1/research/runs/${runId}/web-search`),
    submitWebSearchDecision: (runId: string, approved: boolean, reason?: string) =>
      request<DeepResearchRun>(`/api/v1/research/runs/${runId}/web-search-decision`, {
        method: 'POST',
        body: JSON.stringify({
          approved,
          reason: reason ?? null,
        }),
      }),
    streamRunEvents: streamResearchRunEvents,
  },
  documents: {
    list: (params?: DocumentListParams) => {
      const query = new URLSearchParams();
      if (params?.limit !== undefined) query.set('limit', String(params.limit));
      if (params?.offset !== undefined) query.set('offset', String(params.offset));
      if (params?.search) query.set('search', params.search);
      if (params?.kind) query.set('kind', params.kind);
      const qs = query.toString();
      return request<DocumentListResponse>(`/api/v1/documents${qs ? `?${qs}` : ''}`);
    },
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
