# Contains application configuration values.

import os
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.infrastructure.queue.enums import QueueProvider

_ENV_FILE = ".env.test" if os.getenv("ENVIRONMENT") == "test" else ".env"


class Settings(BaseSettings):
    """
    Application configuration.

    Values are loaded from the local `.env` file during development
    and from environment variables in production.
    """

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        case_sensitive=False,
        extra="ignore",
    )

    # ==========================================================================
    # Application
    # ==========================================================================

    app_name: str = "ResearchMind AI"
    environment: str = "development"
    debug: bool = True
    auto_migrate: bool = False

    # ==========================================================================
    # Database
    # ==========================================================================

    database_url: str = Field(...)
    valkey_url: str = Field(...)
    qdrant_url: str = Field(...)
    qdrant_collection_name: str = "researchmind_knowledge"

    # ==========================================================================
    # Frontend
    # ==========================================================================

    frontend_url: str = "http://localhost:3000"

    # ==========================================================================
    # AI Services
    # ==========================================================================

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None
    groq_api_key: str | None = None
    ollama_enabled: bool = False
    ollama_base_url: str = "http://localhost:11434"
    ollama_timeout_seconds: int = Field(default=120, ge=1)
    langsmith_tracing: bool = False
    langsmith_endpoint: str | None = None
    langsmith_api_key: str | None = None
    langsmith_project: str | None = "ResearchMind"

    # ============================================================================
    # Default Models
    # ============================================================================

    openai_model: str = "gpt-5-mini"

    claude_model: str = "claude-sonnet-5"

    gemini_model: str = "gemini-2.5-flash"

    groq_model: str = "llama-3.3-70b-versatile"

    ollama_model: str = "gemma4:12b"

    # ==========================================================================
    # AWS (Future)
    # ==========================================================================

    aws_region: str = "us-east-1"
    cognito_user_pool_id: str | None = None
    cognito_app_client_id: str | None = None
    cognito_domain: str | None = None
    cognito_client_secret: str | None = None

    # AWS S3
    aws_s3_bucket: str
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_session_token: str | None = None
    aws_s3_endpoint_url: str | None = None

    queue_provider: QueueProvider = QueueProvider.VALKEY

    # AWS SQS
    sqs_queue_url: str = ""

    # Queue

    queue_max_attempts: int = 3
    queue_name: str = "document-processing"
    # ==========================================================================
    # Security
    # ==========================================================================

    secret_key: str = Field(...)
    access_token_expire_minutes: int = 30

    voyage_api_key: str | None = None

    # ==========================================================================
    # Embedding Cache
    # ==========================================================================

    embedding_cache_enabled: bool = True
    embedding_cache_ttl_seconds: int = 60 * 60 * 24 * 30

    # ==========================================================================
    # Query Embedding Cache
    # ==========================================================================

    query_embedding_cache_enabled: bool = True
    query_embedding_cache_ttl_seconds: int = 60 * 60 * 24

    # ==========================================================================
    # Sparse Embeddings (Hybrid Retrieval)
    # ==========================================================================

    sparse_embedding_model: str = "prithivida/Splade_PP_en_v1"

    sparse_embedding_cache_dir: str = os.path.expanduser("~/.cache/researchmind/fastembed")

    # ==========================================================================
    # Reranking
    # ==========================================================================

    cross_encoder_model: str = "BAAI/bge-reranker-base"

    voyage_reranker_model: str = "rerank-2"

    # ==========================================================================
    # Runtime Caching Platform
    # ==========================================================================

    # L1 Exact Cache (Valkey)

    exact_cache_enabled: bool = True
    exact_cache_default_ttl_seconds: int = 60 * 60 * 2  # Chat: 2h
    exact_cache_research_ttl_seconds: int = 60 * 60 * 24  # Research: 24h
    exact_cache_benchmark_ttl_seconds: int | None = None  # Benchmark: infinite

    # L2 Semantic Cache (dedicated RediSearch-capable instance, see
    # docker-compose.yml `semantic-cache` service)

    semantic_cache_enabled: bool = True
    semantic_cache_redis_url: str = "redis://localhost:6380"
    semantic_cache_similarity_threshold: float = 0.92
    semantic_cache_ttl_seconds: int = 60 * 60 * 24
    semantic_cache_embedding_provider: Literal["openai", "voyage_ai"] = "voyage_ai"
    semantic_cache_embedding_model: str = "voyage-3-lite"

    # L3 Session Cache (Valkey)

    session_cache_enabled: bool = True
    session_cache_default_ttl_seconds: int = 60 * 60 * 6

    # ==========================================================================
    # Context Compression
    # ==========================================================================

    enable_langchain_compression: bool = True

    # ==========================================================================
    # Memory Platform
    # ==========================================================================

    # Session Memory (Valkey, PRD §6.1)
    memory_session_ttl_seconds: int = 60 * 60 * 24 * 7  # 7 days

    # Semantic/Research Memory vector index (Qdrant, PRD §6.4)
    memory_qdrant_collection_name: str = "researchmind_memory"
    # Must match the embedding provider/model in use (voyage-3-lite default).
    memory_vector_dimensions: int = 512
    # Minimum cosine similarity for a SEMANTIC/RESEARCH memory to be considered
    # relevant to the current query. Without this, `search()`/`get_context()`
    # always return the nearest `top_k` neighbors even when none of them are
    # actually topically related -- with few memories stored, an unrelated
    # memory from a prior, unrelated conversation can rank in the top_k and
    # get injected into the prompt as if it were relevant context.
    memory_search_score_threshold: float = 0.5

    # Memory runtime optimization. Defaults preserve the established memory
    # contract while allowing each optimization to be rolled back independently.
    memory_durable_retrieval_enabled: bool = True
    memory_durable_availability_cache_enabled: bool = True
    memory_durable_availability_ttl_seconds: int = 120
    memory_parallel_search_enabled: bool = True
    memory_extraction_policy_enabled: bool = True
    memory_extraction_policy_version: str = "v2"
    memory_extraction_min_user_characters: int = 12
    memory_extraction_idempotency_ttl_seconds: int = 60 * 60 * 24 * 7
    # A topic must appear in this many distinct conversations before it can
    # make an otherwise-generic turn eligible for LLM memory extraction.
    # This keeps a single exploratory question out of the user profile.
    memory_interest_promotion_enabled: bool = True
    memory_interest_promotion_min_distinct_sessions: int = 2
    memory_interest_promotion_ttl_seconds: int = 60 * 60 * 24 * 90
    # Canonical Chat/Research history already persists complete turns. Keep
    # raw SESSION copies disabled; only compact, stateful entries belong here.
    memory_session_raw_turn_storage_enabled: bool = False
    memory_session_state_storage_enabled: bool = True
    memory_context_deduplication_enabled: bool = True
    memory_context_session_max_items: int = 5
    memory_context_semantic_max_items: int = 5
    memory_context_research_max_items: int = 5
    memory_context_item_max_characters: int = 500

    # Chat history is paginated for replay. Model context receives recent turns
    # verbatim and a deterministic, persisted summary of older turns; this
    # avoids an extra summarization-model call on the answer path.
    chat_history_page_size: int = 50
    chat_history_page_max_size: int = 100
    chat_prompt_recent_message_limit: int = 12
    chat_prompt_summary_max_characters: int = 4_000

    # Per-owner fixed-window request cap on /chat/stream and /chat/ws --
    # each new chat turn is a real provider-cost call, and nothing else in
    # the request path bounds how many a single account can start.
    chat_rate_limit_requests: int = 20
    chat_rate_limit_window_seconds: int = 60

    # Linear Research (/research, /research/stream, /research/citations) --
    # each call is a retrieval + (for the first two) generation cost, so a
    # tighter default than chat.
    research_rate_limit_requests: int = 15
    research_rate_limit_window_seconds: int = 60

    # Deep Research proposals -- each is an uncached planner LLM call.
    deep_research_proposal_rate_limit_requests: int = 5
    deep_research_proposal_rate_limit_window_seconds: int = 60

    # Deep Research approvals -- the most expensive action in the product:
    # each one queues a real multi-step, multi-LLM-call run (up to $5 /
    # 10 minutes of compute per COMPLEX plan) behind the runtime worker.
    # Deliberately a longer window with a low ceiling.
    deep_research_approval_rate_limit_requests: int = 5
    deep_research_approval_rate_limit_window_seconds: int = 600

    # Research Runtime foundation. The LangGraph workflow is intentionally
    # unavailable to production traffic until durable checkpoint storage and
    # run lifecycle persistence are implemented and verified.
    research_runtime_enabled: bool = False
    research_runtime_postgres_checkpointing_enabled: bool = False
    # Enables the bounded V1 planner -> retrieval waves -> synthesis path.
    # Keep disabled until its canary and resume/replay tests are green.
    research_runtime_v1_graph_enabled: bool = False
    # LangGraph super-step ceiling; a final safety net, not the primary loop
    # control (budgets/iteration caps enforce that). See PRD §25.
    research_runtime_graph_recursion_limit: int = 20
    # A run paused at AWAITING_APPROVAL holds its dispatch slot forever if
    # the user never returns to accept/reject the report. This TTL bounds
    # that wait for `ResearchRunService.expire_stale_awaiting_approval()`,
    # a callable-but-unscheduled sweep (mirrors `MemoryLifecycleService.
    # sweep_stale()`) -- wiring a recurring trigger is an operator decision.
    research_runtime_awaiting_approval_ttl_hours: int = 72
    # Concurrent dispatch-claim lanes run in-process by
    # `research_runtime_main.py`, each with its own DB session. The Postgres
    # outbox (`SELECT ... FOR UPDATE SKIP LOCKED`) already makes concurrent
    # claims safe (see `ResearchRunDispatchRepository.claim_next`), so this
    # is the cheapest throughput knob; running more OS processes/containers
    # of the same entrypoint is equally safe and composes with this (see
    # REMAINING_WORK.md D2).
    research_runtime_worker_concurrency: int = 1

    # Load-shedding: total PENDING+RUNNING dispatch rows allowed before
    # `/proposals/{id}/approve` starts rejecting new approvals with 503, so
    # demand exceeding worker throughput degrades as an explicit
    # client-visible retry signal instead of an unbounded, invisible queue
    # (REMAINING_WORK.md D2).
    deep_research_max_queued_runs: int = 20
    deep_research_queue_full_retry_after_seconds: int = 60

    # Web Search Tool Platform (web_search_tool_platform_prd.md). Default-off
    # at both the platform level (`web_search_enabled`) and per-request
    # (`WebSearchMode.DISABLED`) -- existing Deep Research runs are
    # unaffected until a caller opts in and this is enabled.
    web_search_enabled: bool = True
    tavily_api_key: str | None = None
    web_search_max_calls_per_run: int = 1
    web_search_max_results_per_call: int = 8
    web_search_timeout_seconds: float = 20.0
    # Dedicated cheap-tier models for the web-search necessity decision only
    # -- deliberately separate from `openai_model`/`claude_model`, which
    # apply to every other generation call (synthesis, review, etc.). See
    # `app.ai.runtime.research.web_search.create`. `gpt-5-mini`, not the
    # cheaper `gpt-5-nano`: confirmed in production that `gpt-5-nano`
    # unreliably follows the structured-output (`json_schema`) contract for
    # this call, exhausting the regeneration budget and silently failing
    # closed to "no search needed" every time (2026-07-25). `gpt-5-mini` is
    # this app's already-proven-reliable default OpenAI model everywhere
    # else; still materially cheaper than the main synthesis/review tier.
    web_search_decision_openai_model: str = "gpt-5-mini"
    web_search_decision_claude_model: str = "claude-haiku-4-5"

    # Dedicated cheap-tier models for the feedback-comment objective/
    # preference classification call only (E11, EVALUATION_PLAN.md §12/
    # 1g) -- same isolation rationale as `web_search_decision_*` above,
    # and the same `gpt-5-mini` choice over `gpt-5-nano` for the same
    # structured-output-reliability reason, not yet independently
    # reconfirmed for this specific call but treated as the safer default
    # given the identical schema shape. See
    # `app.ai.runtime.generation.comment_classification.create`.
    comment_classification_openai_model: str = "gpt-5-mini"
    comment_classification_claude_model: str = "claude-haiku-4-5"

    # Research Intelligence MCP Platform (paper search over MCP streamable-http,
    # prds/3. mcp_server_setup.md). `mcp_papers_server_url` absent degrades
    # `PaperSearchService.available` to `False` rather than raising -- mirrors
    # `tavily_api_key`'s "unconfigured deployment never crashes" convention.
    mcp_papers_enabled: bool = True
    mcp_papers_server_url: str | None = None
    mcp_papers_auth_token: str | None = None
    mcp_papers_timeout_seconds: float = 60.0
    mcp_papers_max_results_per_call: int = 5
    mcp_papers_cache_enabled: bool = True
    mcp_papers_cache_ttl_seconds: int = 3600
    mcp_papers_query_provider: Literal["auto", "groq", "openai", "claude", "gemini", "ollama"] = (
        "auto"
    )
    # Dedicated cheap-tier models for Chat's paper-search query-extraction
    # call only -- deliberately separate from `openai_model`/`claude_model`
    # (same reasoning as `web_search_decision_openai_model`: isolates this
    # one bounded call's model choice from the rest of the app). Confirmed
    # in production (2026-07-25) that sending the raw chat message straight
    # to search_papers returns zero results for conversational phrasing.
    mcp_papers_query_openai_model: str = "gpt-5-mini"
    mcp_papers_query_claude_model: str = "claude-haiku-4-5"

    # Importance scoring (PRD §16)
    memory_importance_threshold: float = 0.1

    # ==========================================================================
    # Prometheus / Grafana Observability (prometheus_grafana_observability_prd.md)
    # ==========================================================================

    prometheus_enabled: bool = True
    prometheus_metrics_path: str = "/metrics"
    prometheus_include_http_metrics: bool = True
    prometheus_include_runtime_metrics: bool = True
    prometheus_include_process_metrics: bool = True
    prometheus_include_platform_metrics: bool = True

    grafana_admin_user: str = "admin"
    grafana_admin_password: str = "admin"
    grafana_port: int = 3001

    prometheus_port: int = 9090
    prometheus_scrape_interval_seconds: int = 15
    prometheus_retention_time: str = "15d"

    @field_validator("prometheus_metrics_path")
    @classmethod
    def _validate_prometheus_metrics_path(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError("prometheus_metrics_path must begin with '/'.")
        return value

    @field_validator("grafana_port", "prometheus_port")
    @classmethod
    def _validate_port_range(cls, value: int) -> int:
        if not (0 < value < 65536):
            raise ValueError("Port must be between 1 and 65535.")
        return value

    @field_validator("prometheus_scrape_interval_seconds")
    @classmethod
    def _validate_scrape_interval(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("prometheus_scrape_interval_seconds must be positive.")
        return value

    @field_validator("prometheus_retention_time")
    @classmethod
    def _validate_retention_time(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("prometheus_retention_time must not be empty.")
        return value

    # ==========================================================================
    # Online Evaluation Scoring (EVALUATION_PLAN.md §14, E5)
    # ==========================================================================

    eval_online_baseline_sample_rate: float = 0.075
    """Flat baseline sample rate for LLM-judge scoring on requests that
    aren't guardrail-flagged, non-PASS-reviewed, or in a canary window --
    EVALUATION_PLAN.md §14's 5-10% baseline, defaulting to the midpoint."""

    eval_online_canary_oversample_rate: float = 0.5
    eval_online_canary_prompt_version: str | None = None
    """When set, generations tagged with this `prompt_version` are
    oversampled at `eval_online_canary_oversample_rate` instead of the
    flat baseline -- EVALUATION_PLAN.md §14's "config-fingerprint canary
    window" row. Deliberately simple for this MVP pass: a single
    prompt_version string to watch, not a full canary-deployment/traffic-
    splitting system (out of scope, see PRIORITIZED_ROADMAP.md's 1f note
    on deferred live A/B traffic splitting)."""

    eval_online_batch_size: int = 25
    eval_online_poll_interval_seconds: float = 30.0
    eval_online_lookback_hours: float = 24.0
    """How far back `list_unscored_since()` looks on each tick -- bounds
    the anti-join scan; a generation older than this that somehow never
    got scored stays unscored rather than being picked up on every poll
    forever."""

    @field_validator(
        "eval_online_baseline_sample_rate",
        "eval_online_canary_oversample_rate",
    )
    @classmethod
    def _validate_sample_rate(cls, value: float) -> float:
        if not (0.0 <= value <= 1.0):
            raise ValueError("Sample rates must be between 0.0 and 1.0.")
        return value

    # ==========================================================================
    # Internal Eval Dashboard (EVALUATION_PLAN.md §16 phase 8, E7)
    # ==========================================================================

    eval_dashboard_admin_emails: str = ""
    """
    Comma-separated allowlist of user emails permitted to view the
    internal eval dashboard (`GET /api/v1/eval-dashboard/*`). Plain
    `str`, not `list[str]`: pydantic-settings would otherwise require
    JSON-array syntax (`["a@b.com"]`) in `.env`, which is less ergonomic
    than a comma-separated value for an operator to set. Empty by
    default -- no one has access until this is explicitly configured.
    Deliberately a settings-based allowlist, not a `User.is_admin`
    column: this is internal engineering tooling, not a customer-facing
    feature, and a real RBAC column with no admin-management UI to set
    it would be more schema/scope than the need justifies today.
    """

    def eval_dashboard_admin_email_set(self) -> set[str]:
        return {
            email.strip().lower()
            for email in self.eval_dashboard_admin_emails.split(",")
            if email.strip()
        }

    def is_eval_dashboard_admin(self, email: str) -> bool:
        """Single source of truth for the allowlist check -- shared by
        `require_eval_dashboard_access` (the real gate, every
        `/eval-dashboard/*` request) and `GET /auth/me` (presentation
        only, drives whether the frontend shows the nav link)."""

        return email.strip().lower() in self.eval_dashboard_admin_email_set()


settings = Settings()  # pyright: ignore[reportCallIssue]
