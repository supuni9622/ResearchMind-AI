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
  // Presentation only -- drives whether the sidebar shows the internal
  // eval dashboard link. The real access gate is server-side, checked
  // fresh on every /api/v1/eval-dashboard/* request (E7).
  eval_dashboard_access: boolean;
}

export type DocumentUploadStatus = 'pending' | 'uploading' | 'completed' | 'failed';
export type DocumentProcessingStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface Document {
  id: string;
  project_id: string | null;
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
  // Omitted -> personal documents only, not "every project" -- same
  // contract as api.chat.listConversations.
  projectId?: string | null;
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

export type MemoryType = 'session' | 'user' | 'semantic' | 'research';

// Injected into every context (personal and every project) -- see
// MemoryScopeType.GLOBAL on the backend.
export type MemoryScope = 'personal' | 'project' | 'global';

export interface MemoryRecord {
  id: string;
  scope_type: MemoryScope;
  project_id: string | null;
  type: MemoryType;
  content: string;
  source: string | null;
  confidence: number | null;
  origin: 'explicit' | 'inferred';
  last_used_at: string | null;
  editable: boolean;
  created_at: string;
  updated_at: string;
}

export interface MemoryListResponse {
  memories: MemoryRecord[];
  total: number;
  limit: number;
  offset: number;
}

export interface MemoryListParams {
  search?: string;
  source?: string;
  type?: MemoryType[];
  scope_type?: MemoryScope;
  project_id?: string;
  created_from?: string;
  created_to?: string;
  updated_from?: string;
  updated_to?: string;
  origin?: 'explicit' | 'inferred';
  limit?: number;
  offset?: number;
}

export interface MemoryScopeSettings {
  scope_type: MemoryScope;
  project_id: string | null;
  capture_enabled: boolean;
  retrieval_enabled: boolean;
  inherit_personal_memory: boolean;
  retention_enabled: boolean;
}

export interface MemoryProject {
  id: string;
  name: string;
  role: string;
}

export interface Project {
  id: string;
  name: string;
  description: string | null;
  role: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectListResponse {
  projects: Project[];
}

export interface MemoryDeletionPreview {
  confirmation_token: string;
  affected_count: number;
  scope_type: MemoryScope;
  project_id: string | null;
  expires_at: string;
  immediate_erasure: boolean;
}

export interface MemoryGovernanceJob {
  id: string;
  scope_type: MemoryScope;
  project_id: string | null;
  status: 'pending' | 'running' | 'completed' | 'failed';
  requested_count: number;
  deleted_postgres: number;
  deleted_qdrant: number;
  deleted_valkey: number;
  deleted_artifacts: number;
  failure_stage: string | null;
  completed_at: string | null;
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
  score: number;
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
  generation_id: string | null;
  memory_used: boolean;
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
  /** E21: read from the persisted final-report.json artifact; null for
   * reports persisted before this field existed. */
  generation_id: string | null;
  memory_used: boolean;
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
  retry_count: number;
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
  model_quality_score: number | null;
  gap_questions: string[];
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
  socratic_question: string | null;
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
  /** Only meaningful when starting a brand-new conversation -- ignored
   * once `conversationId` is set, matching the backend's
   * `authorize_for_new_conversation` contract. */
  projectId?: string | null;
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

// Matches `app/models/enums.py::FeedbackRating`/`FeedbackSurface` (E21,
// EVALUATION_PLAN.md §16 phase 3).
export type FeedbackRating = 'up' | 'down';
export type FeedbackSurface = 'chat' | 'linear_research' | 'deep_research';
export type MemoryFeedbackSignal = 'helped' | 'wrong';

export interface FeedbackResponse {
  id: string;
  generation_id: string;
  surface: FeedbackSurface;
  rating: FeedbackRating;
  comment: string | null;
  created_at: string;
  updated_at: string;
}

// Internal eval dashboard (E7, EVALUATION_PLAN.md §16 phase 8). Every
// route behind this is gated server-side by an email allowlist
// (`settings.eval_dashboard_admin_emails`) -- a non-allowlisted caller
// gets a 403 `ApiError`, handled by the page itself, not hidden here.
export interface EvalScore {
  id: string;
  generation_id: string | null;
  metric_name: string;
  score: number | null;
  passed: boolean | null;
  reason: string | null;
  source: string;
  sample_category: string | null;
  dataset_example_id: string | null;
  comment_classification: string | null;
  created_at: string;
}

export interface EvalScoreListResponse {
  items: EvalScore[];
  total: number;
  limit: number;
  offset: number;
}

export interface OwnerSummary {
  owner_id: string;
  email: string;
  username: string | null;
  score_count: number;
}

export interface OwnerListResponse {
  items: OwnerSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface ReviewDecisionDistribution {
  owner_id: string;
  counts: Record<string, number>;
}

export interface OfflineExampleSummary {
  dataset_example_id: string;
  score_count: number;
  latest_run_at: string;
}

export interface OfflineExampleListResponse {
  items: OfflineExampleSummary[];
  total: number;
  limit: number;
  offset: number;
}

// Engineering benchmarks (chunking/embeddings/retrieval/reranking/
// generation-provider-comparison) -- read-only, straight off
// `benchmarks/reports/*/report.json`. No history/trends: just whatever
// each benchmark's last local run produced. GoldenSetGeneration/
// ProductionFailuresRegression are excluded from this endpoint (see
// OfflineExampleSummary above for their dedicated per-example view) --
// but `offlineSummary()` below surfaces their *aggregate* metrics
// (e.g. rubric_adherence) using this same shape, since the per-example
// view has no place to show that number.
export interface BenchmarkCandidateResult {
  name: string;
  version: string | null;
  metrics: Record<string, number | string | boolean>;
  notes: Record<string, unknown>;
}

export interface BenchmarkReportResult {
  benchmark_name: string;
  generated_at: string;
  dataset: { name: string; document_count: number };
  metadata: {
    git_commit: string | null;
    branch: string | null;
    dataset_version: string;
    model_versions: Record<string, string>;
    benchmark_version: string;
    timestamp: string;
  };
  candidates: BenchmarkCandidateResult[];
  summary: Record<string, unknown>;
}

// Segment analysis (E9) -- two dimensions, because that's genuinely what
// the data supports: online-sampled rows can be grouped by a
// GenerationUsage config-fingerprint field (prompt_version etc.), since
// only those rows have a generation_usage row to join against.
// Offline-benchmark rows have no fingerprint, but do have a
// dataset_example_id resolvable to the golden set's query_type/
// difficulty/workflow -- a different join, a different tab.
export type FingerprintField =
  | 'surface'
  | 'prompt_version'
  | 'chunking_strategy'
  | 'embedding_model'
  | 'reranker'
  | 'routing_strategy';

export type ContentSegmentField = 'query_type' | 'difficulty' | 'workflow' | 'failure_category';

export interface FingerprintSegmentAggregate {
  fingerprint_value: string | null;
  count: number;
  avg_score: number | null;
  pass_rate: number | null;
}

export interface FingerprintSegmentAnalysisResponse {
  metric_name: string;
  fingerprint_field: string;
  items: FingerprintSegmentAggregate[];
}

export interface ContentSegmentAggregate {
  segment_value: string;
  count: number;
  avg_score: number | null;
  pass_rate: number | null;
}

export interface ContentSegmentAnalysisResponse {
  metric_name: string;
  segment_field: string;
  items: ContentSegmentAggregate[];
}

// Promotion review (E10) -- the closing step of the offline-gates ->
// deploy -> traces -> free checks -> sampled judges -> review queue ->
// confirmed promotion -> re-run-in-CI loop (EVALUATION_PLAN.md §15).
// This app never stores/replays the original question/answer/context
// (see PromotionReview's own backend docstring for why) -- a reviewer
// reads the real content via the LangSmith trace link, then fills in
// this form by hand.
export type PromotionDirection = 'good' | 'failure';

// Which unreviewed-candidate list to fetch -- distinct from
// PromotionDirection (what a *confirmed* row becomes): 'preference' never
// becomes its own dataset, it's thumbs-down feedback E11 classified
// 'preference' rather than 'objective', surfaced separately so a reviewer
// can override the classifier instead of it vanishing from the queue.
export type PromotionCandidateView = PromotionDirection | 'preference';

export interface PromotionCandidate {
  source: string;
  owner_id: string;
  generation_id: string;
  reason: string;
  created_at: string;
}

export interface PromotionCandidateListResponse {
  items: PromotionCandidate[];
  total: number;
  limit: number;
  offset: number;
}

export type PromotionQueryType = 'factual' | 'synthesis' | 'comparison' | 'exploratory' | 'unanswerable';
export type PromotionDifficulty = 'easy' | 'medium' | 'hard';
export type PromotionWorkflow = 'chat' | 'linear_research' | 'deep_research';
export type PromotionFailureCategory =
  | 'wrong_citation'
  | 'hallucination'
  | 'retrieval_miss'
  | 'unnecessary_tool_use'
  | 'abstention_failure'
  | 'workflow_loop'
  | 'schema_violation'
  | 'injection_success';

export interface ConfirmPromotionPayload {
  source: string;
  direction: PromotionDirection;
  owner_id: string;
  generation_id: string;
  question: string;
  reference_answer: string;
  contexts: string[];
  reference_context_ids: string[];
  expected_citation_ids: string[];
  query_type: PromotionQueryType;
  difficulty: PromotionDifficulty;
  workflow: PromotionWorkflow;
  rubric?: string | null;
  failure_category?: PromotionFailureCategory | null;
}

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
  /** Only meaningful when starting a brand-new conversation -- ignored
   * once `conversationId` is set, matching the backend's
   * `authorize_for_new_conversation` contract. */
  projectId?: string | null;
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
        project_id: options.projectId ?? null,
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
  /** Only consulted when starting a new conversation (no `conversationId`)
   * -- an existing conversation keeps whatever project it already belongs
   * to. `null`/undefined means personal. */
  projectId?: string | null;
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
  project_id: string | null;
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
        project_id: options.projectId ?? null,
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
  memory: {
    projects: () => request<MemoryProject[]>('/api/v1/memory/projects'),
    exportScope: (scopeType: MemoryScope, projectId?: string) => {
      const query = new URLSearchParams({ scope_type: scopeType });
      if (projectId) query.set('project_id', projectId);
      return request<Record<string, unknown>>(`/api/v1/memory/export?${query.toString()}`);
    },
    previewDeletion: (
      scopeType: MemoryScope,
      projectId: string | undefined,
      memoryIds: string[] | null,
      signal?: AbortSignal
    ) => request<MemoryDeletionPreview>('/api/v1/memory/deletion/preview', {
      method: 'POST',
      signal,
      body: JSON.stringify({
        scope_type: scopeType,
        project_id: projectId ?? null,
        memory_ids: memoryIds,
      }),
    }),
    executeDeletion: (confirmationToken: string) =>
      request<MemoryGovernanceJob>('/api/v1/memory/deletion/jobs', {
        method: 'POST',
        body: JSON.stringify({ confirmation_token: confirmationToken }),
      }),
    getDeletionJob: (jobId: string) =>
      request<MemoryGovernanceJob>(`/api/v1/memory/deletion/jobs/${jobId}`),
    retryDeletion: (jobId: string) =>
      request<MemoryGovernanceJob>(`/api/v1/memory/deletion/jobs/${jobId}/retry`, {
        method: 'POST',
      }),
    list: (params: MemoryListParams = {}) => {
      const query = new URLSearchParams();
      if (params.search) query.set('search', params.search);
      if (params.source) query.set('source', params.source);
      params.type?.forEach((memoryType) => query.append('type', memoryType));
      if (params.scope_type) query.set('scope_type', params.scope_type);
      if (params.project_id) query.set('project_id', params.project_id);
      if (params.created_from) query.set('created_from', params.created_from);
      if (params.created_to) query.set('created_to', params.created_to);
      if (params.updated_from) query.set('updated_from', params.updated_from);
      if (params.updated_to) query.set('updated_to', params.updated_to);
      if (params.origin) query.set('origin', params.origin);
      query.set('limit', String(params.limit ?? 10));
      query.set('offset', String(params.offset ?? 0));
      return request<MemoryListResponse>(`/api/v1/memory?${query.toString()}`);
    },
    update: (memory: MemoryRecord, content: string) => {
      const query = new URLSearchParams({ scope_type: memory.scope_type });
      if (memory.project_id) query.set('project_id', memory.project_id);
      return request<MemoryRecord>(`/api/v1/memory/${memory.id}?${query.toString()}`, {
        method: 'PUT',
        body: JSON.stringify({ type: memory.type, content }),
      });
    },
    delete: (memory: MemoryRecord) => {
      const query = new URLSearchParams({ scope_type: memory.scope_type });
      if (memory.project_id) query.set('project_id', memory.project_id);
      return request<void>(`/api/v1/memory/${memory.id}?${query.toString()}`, {
        method: 'DELETE',
      });
    },
    getSettings: (scopeType: MemoryScope, projectId?: string) => {
      const query = new URLSearchParams({ scope_type: scopeType });
      if (projectId) query.set('project_id', projectId);
      return request<MemoryScopeSettings>(`/api/v1/memory/settings?${query.toString()}`);
    },
    updateSettings: (settings: Omit<MemoryScopeSettings, 'retention_enabled'>) =>
      request<MemoryScopeSettings>('/api/v1/memory/settings', {
        method: 'PUT',
        body: JSON.stringify(settings),
      }),
    move: (
      memoryId: string,
      source: { scope_type: MemoryScope; project_id: string | null },
      destination: { scope_type: MemoryScope; project_id: string | null }
    ) =>
      request<MemoryRecord>(`/api/v1/memory/${memoryId}/move`, {
        method: 'POST',
        body: JSON.stringify({
          source_scope_type: source.scope_type,
          source_project_id: source.project_id,
          scope_type: destination.scope_type,
          project_id: destination.project_id,
          confirmed: true,
        }),
      }),
  },
  projects: {
    list: () => request<ProjectListResponse>('/api/v1/projects'),
    create: (input: { name: string; description?: string | null }) =>
      request<Project>('/api/v1/projects', {
        method: 'POST',
        body: JSON.stringify({ name: input.name, description: input.description ?? null }),
      }),
    update: (projectId: string, input: { name?: string; description?: string | null }) =>
      request<Project>(`/api/v1/projects/${projectId}`, {
        method: 'PATCH',
        body: JSON.stringify(input),
      }),
    delete: (projectId: string) =>
      request<void>(`/api/v1/projects/${projectId}`, { method: 'DELETE' }),
  },
  chat: {
    stream: streamChat,
    // `projectId` omitted/null -> personal conversations only, matching
    // the backend's `GET /chat/conversations` contract -- this endpoint
    // never returns "everything across every workspace" implicitly.
    listConversations: (cursor?: string, projectId?: string | null) => {
      const params = new URLSearchParams();
      if (cursor) params.set('cursor', cursor);
      if (projectId) params.set('project_id', projectId);
      const query = params.toString();
      return request<ChatConversationListResponse>(
        `/api/v1/chat/conversations${query ? `?${query}` : ''}`
      );
    },
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
          project_id: options.projectId ?? null,
        }),
      }),
    stream: streamResearch,
    get: (researchId: string) =>
      request<ResearchSessionResponse>(`/api/v1/research/${researchId}`),
    // `projectId` omitted/null -> personal conversations only, matching
    // the backend's `GET /research/conversations` contract.
    listConversations: (projectId?: string | null) => {
      const params = new URLSearchParams();
      if (projectId) params.set('project_id', projectId);
      const query = params.toString();
      return request<ResearchConversationListResponse>(
        `/api/v1/research/conversations${query ? `?${query}` : ''}`
      );
    },
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
          project_id: options.projectId ?? null,
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
          project_id: options.projectId ?? null,
          web_search_mode: options.webSearchMode ?? 'disabled',
          web_search_auto_approve: options.webSearchAutoApprove ?? false,
          include_domains: options.includeDomains ?? [],
          exclude_domains: options.excludeDomains ?? [],
          paper_suggestions_enabled: options.paperSuggestionsEnabled ?? false,
          socratic_challenger_enabled: true,
        }),
      }),
    approveProposal: (proposalId: string) =>
      request<DeepResearchRun>(`/api/v1/research/proposals/${proposalId}/approve`, {
        method: 'POST',
      }),
    getRun: (runId: string) => request<DeepResearchRun>(`/api/v1/research/runs/${runId}`),
    cancelRun: (runId: string) =>
      request<DeepResearchRun>(`/api/v1/research/runs/${runId}/cancel`, { method: 'POST' }),
    retryRun: (runId: string) =>
      request<DeepResearchRun>(`/api/v1/research/runs/${runId}/retry`, { method: 'POST' }),
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
    submitPlanDecision: (
      runId: string,
      approved: boolean,
      reason?: string,
      editedGoal?: string,
      socraticResponse?: string
    ) =>
      request<DeepResearchRun>(`/api/v1/research/runs/${runId}/plan-decision`, {
        method: 'POST',
        body: JSON.stringify({
          approved,
          reason: reason ?? null,
          edited_plan: editedGoal ? { rewritten_goal: editedGoal } : null,
          socratic_response: socraticResponse || null,
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
      if (params?.projectId) query.set('project_id', params.projectId);
      const qs = query.toString();
      return request<DocumentListResponse>(`/api/v1/documents${qs ? `?${qs}` : ''}`);
    },
    stats: (projectId?: string | null) => {
      const query = new URLSearchParams();
      if (projectId) query.set('project_id', projectId);
      const qs = query.toString();
      return request<DocumentKnowledgeStats>(`/api/v1/documents/stats${qs ? `?${qs}` : ''}`);
    },
    upload: async (file: File, projectId?: string | null): Promise<Document> => {
      const token = getStoredToken();
      const form = new FormData();
      form.append('file', file);
      if (projectId) form.append('project_id', projectId);

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
    delete: (documentId: string) =>
      request<void>(`/api/v1/documents/${documentId}`, { method: 'DELETE' }),
  },

  feedback: {
    // Idempotent server-side (upsert on (owner_id, generation_id)) --
    // resubmitting for the same generation_id updates the existing
    // rating/comment rather than erroring, so re-clicking is safe.
    submit: (
      generationId: string,
      surface: FeedbackSurface,
      rating: FeedbackRating,
      comment?: string
    ) =>
      request<FeedbackResponse>('/api/v1/feedback', {
        method: 'POST',
        body: JSON.stringify({
          generation_id: generationId,
          surface,
          rating,
          comment: comment ?? null,
        }),
      }),
    submitMemory: (
      generationId: string,
      surface: FeedbackSurface,
      signal: MemoryFeedbackSignal
    ) =>
      request('/api/v1/feedback/memory', {
        method: 'POST',
        body: JSON.stringify({ generation_id: generationId, surface, signal }),
      }),
  },

  evalDashboard: {
    listOwners: (params?: { search?: string; limit?: number; offset?: number }) => {
      const query = new URLSearchParams();
      if (params?.search) query.set('search', params.search);
      if (params?.limit !== undefined) query.set('limit', String(params.limit));
      if (params?.offset !== undefined) query.set('offset', String(params.offset));
      const qs = query.toString();
      return request<OwnerListResponse>(`/api/v1/eval-dashboard/owners${qs ? `?${qs}` : ''}`);
    },
    listScores: (
      ownerId: string,
      params?: { metricName?: string; source?: string; limit?: number; offset?: number }
    ) => {
      const query = new URLSearchParams({ owner_id: ownerId });
      if (params?.metricName) query.set('metric_name', params.metricName);
      if (params?.source) query.set('source', params.source);
      if (params?.limit !== undefined) query.set('limit', String(params.limit));
      if (params?.offset !== undefined) query.set('offset', String(params.offset));
      return request<EvalScoreListResponse>(`/api/v1/eval-dashboard/scores?${query.toString()}`);
    },
    reviewDecisions: (ownerId: string) =>
      request<ReviewDecisionDistribution>(
        `/api/v1/eval-dashboard/review-decisions?owner_id=${ownerId}`
      ),
    // Offline (golden-set benchmark) results -- deliberately separate
    // from listOwners/listScores above: offline rows have no owner_id
    // (they score a fixed dataset example, not a live generation), so
    // they can never appear in the owner-scoped endpoints.
    listOfflineExamples: (params?: { search?: string; limit?: number; offset?: number }) => {
      const query = new URLSearchParams();
      if (params?.search) query.set('search', params.search);
      if (params?.limit !== undefined) query.set('limit', String(params.limit));
      if (params?.offset !== undefined) query.set('offset', String(params.offset));
      const qs = query.toString();
      return request<OfflineExampleListResponse>(
        `/api/v1/eval-dashboard/offline-examples${qs ? `?${qs}` : ''}`
      );
    },
    listOfflineScores: (params?: {
      datasetExampleId?: string;
      metricName?: string;
      limit?: number;
      offset?: number;
    }) => {
      const query = new URLSearchParams();
      if (params?.datasetExampleId) query.set('dataset_example_id', params.datasetExampleId);
      if (params?.metricName) query.set('metric_name', params.metricName);
      if (params?.limit !== undefined) query.set('limit', String(params.limit));
      if (params?.offset !== undefined) query.set('offset', String(params.offset));
      const qs = query.toString();
      return request<EvalScoreListResponse>(
        `/api/v1/eval-dashboard/offline-scores${qs ? `?${qs}` : ''}`
      );
    },
    listBenchmarkReports: () =>
      request<BenchmarkReportResult[]>('/api/v1/eval-dashboard/benchmark-reports'),
    offlineSummary: () =>
      request<BenchmarkReportResult[]>('/api/v1/eval-dashboard/offline-summary'),
    segmentAnalysisOnline: (params: { metricName: string; fingerprintField: FingerprintField }) => {
      const query = new URLSearchParams({
        metric_name: params.metricName,
        fingerprint_field: params.fingerprintField,
      });
      return request<FingerprintSegmentAnalysisResponse>(
        `/api/v1/eval-dashboard/segment-analysis/online?${query.toString()}`
      );
    },
    segmentAnalysisOffline: (params: { metricName: string; segmentField: ContentSegmentField }) => {
      const query = new URLSearchParams({
        metric_name: params.metricName,
        segment_field: params.segmentField,
      });
      return request<ContentSegmentAnalysisResponse>(
        `/api/v1/eval-dashboard/segment-analysis/offline?${query.toString()}`
      );
    },
  },

  promotionReview: {
    listCandidates: (params: {
      direction: PromotionCandidateView;
      limit?: number;
      offset?: number;
    }) => {
      const query = new URLSearchParams({ direction: params.direction });
      if (params.limit !== undefined) query.set('limit', String(params.limit));
      if (params.offset !== undefined) query.set('offset', String(params.offset));
      return request<PromotionCandidateListResponse>(
        `/api/v1/eval-dashboard/promotion-review/candidates?${query.toString()}`
      );
    },
    traceUrl: (generationId: string) =>
      request<{ trace_url: string | null }>(
        `/api/v1/eval-dashboard/promotion-review/trace-url?generation_id=${generationId}`
      ),
    reject: (payload: { source: string; owner_id: string; generation_id: string }) =>
      request('/api/v1/eval-dashboard/promotion-review/reject', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    confirm: (payload: ConfirmPromotionPayload) =>
      request('/api/v1/eval-dashboard/promotion-review/confirm', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
  },
};
