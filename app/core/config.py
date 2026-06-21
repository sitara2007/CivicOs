"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=None if os.getenv("PYTEST_CURRENT_TEST") else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    log_level: str = "INFO"
    port: int = 8000
    service_name: str = "CivicOs"
    service_version: str = "0.1.0"
    api_prefix: str = "/api/v1"

    database_url: str = Field(
        "",
        env=["DATABASE_URL", "POSTGRES_URL"],
    )
    database_enabled: bool = True
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str | None = None
    qdrant_url: str = Field("", env=["QDRANT_URL"])

    openai_api_key: str = Field("", env=["OPENAI_API_KEY", "LLM_API_KEY"])
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    rag_enabled: bool = True
    rag_embedding_model: str = "all-MiniLM-L6-v2"
    rag_qdrant_path: str = "data/qdrant_db"
    rag_collection_name: str = "gov_docs"
    rag_top_k: int = 3
    rag_context_max_chars: int = 4_000

    max_agentic_hops: int = 5
    review_confidence_threshold: float = 0.75
    max_input_tokens: int = 8000
    max_document_tokens: int = 10_000
    sync_mode: bool = True  # Phase 1-4: sync; Phase 5+: set False
    mock_llm: bool = False  # set MOCK_LLM=true for offline demo / CI

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
    return Settings()
