"""Application settings loaded from environment variables."""

from __future__ import annotations
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # --- Critical Settings ---
    # Agar ye .env mein nahi mile, toh app start nahi hogi (Fail-Fast)
    openai_api_key: str = Field(validation_alias="OPENAI_API_KEY")
    database_url: str = Field(default="", validation_alias="DATABASE_URL")
    qdrant_url: str = Field(default="", validation_alias="QDRANT_URL")

    # --- Application Configuration ---
    environment: str = Field(default="development", validation_alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    port: int = Field(default=8000, validation_alias="PORT")
    service_name: str = Field(default="CivicOs", validation_alias="SERVICE_NAME")
    service_version: str = Field(default="0.1.0", validation_alias="SERVICE_VERSION")
    api_prefix: str = Field(default="/api/v1", validation_alias="API_PREFIX")

    # --- Database & Broker ---
    database_enabled: bool = Field(default=True, validation_alias="DATABASE_ENABLED")
    redis_url: str = Field(default="redis://localhost:6379/0", validation_alias="REDIS_URL")
    celery_broker_url: str | None = Field(default=None, validation_alias="CELERY_BROKER_URL")

    # --- LLM Settings ---
    openai_model: str = Field(default="gpt-4o-mini", validation_alias="OPENAI_MODEL")
    openai_embedding_model: str = Field(default="text-embedding-3-small", validation_alias="OPENAI_EMBEDDING_MODEL")

    # --- RAG Settings ---
    rag_enabled: bool = Field(default=True, validation_alias="RAG_ENABLED")
    rag_embedding_model: str = Field(default="all-MiniLM-L6-v2", validation_alias="RAG_EMBEDDING_MODEL")
    rag_qdrant_path: str = Field(default="data/qdrant_db", validation_alias="RAG_QDRANT_PATH")
    rag_collection_name: str = Field(default="gov_docs", validation_alias="RAG_COLLECTION_NAME")
    rag_top_k: int = Field(default=3, validation_alias="RAG_TOP_K")
    rag_context_max_chars: int = Field(default=4_000, validation_alias="RAG_CONTEXT_MAX_CHARS")
    rag_qdrant_timeout_ms: int = Field(default=300, validation_alias="RAG_QDRANT_TIMEOUT_MS")

    # --- Agentic & Review Settings ---
    max_agentic_hops: int = Field(default=5, validation_alias="MAX_AGENTIC_HOPS")
    review_confidence_threshold: float = Field(default=0.75, validation_alias="REVIEW_CONFIDENCE_THRESHOLD")
    max_input_tokens: int = Field(default=8000, validation_alias="MAX_INPUT_TOKENS")
    max_document_tokens: int = Field(default=10_000, validation_alias="MAX_DOCUMENT_TOKENS")
    sync_mode: bool = Field(default=True, validation_alias="SYNC_MODE")
    mock_llm: bool = Field(default=False, validation_alias="MOCK_LLM")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def use_mock_llm(self) -> bool:
        if self.mock_llm:
            return True
        return self.environment == "development" and not self.openai_api_key

    @property
    def broker_url(self) -> str:
        return self.celery_broker_url or self.redis_url

@lru_cache
def get_settings() -> Settings:
    # Pydantic sab handle kar lega, koi override ki zaroorat nahi
    return Settings()