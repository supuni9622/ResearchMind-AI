# Contains application configuration values.

import os

from pydantic import Field
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
    ollama_host: str = "http://localhost:11434"
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

    ollama_model: str = "qwen3:latest"

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
    semantic_cache_embedding_model: str = "text-embedding-3-small"

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

    # Importance scoring (PRD §16)
    memory_importance_threshold: float = 0.1


settings = Settings()  # pyright: ignore[reportCallIssue]
