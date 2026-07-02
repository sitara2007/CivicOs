"""FastAPI application entrypoint for CivicOs."""
from __future__ import annotations

import os
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging

logger = logging.getLogger("app.main")


def validate_required_environment() -> None:
    """Fail fast when required startup environment variables are missing."""

    settings = get_settings()
    missing: list[str] = []

    if settings.database_enabled and not settings.database_url.strip():
        missing.append("POSTGRES_URL or DATABASE_URL")

    # Accept either OPENAI_API_KEY or LLM_API_KEY aliases when present in the
    # environment. Use the helper in `app.core.config` to check supported names
    # so tests that set `LLM_API_KEY` are honored.
    # Check the environment directly for supported aliases to ensure values
    # set via test fixtures (monkeypatch) are respected even if settings were
    # previously loaded/cached elsewhere during test module import.
    env_openai = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    openai_key = settings.openai_api_key or (env_openai or "")
    if not settings.use_mock_llm and not openai_key.strip():
        missing.append("LLM_API_KEY or OPENAI_API_KEY")

    if missing:
        missing_vars = ", ".join(missing)
        raise RuntimeError(f"Missing required environment variable(s): {missing_vars}")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown concerns."""

    validate_required_environment()
    settings = get_settings()
    logger.info(
        "application_starting",
        extra={
            "service": settings.service_name,
            "version": settings.service_version,
            "environment": settings.environment,
        },
    )
    app.state.settings = settings

    try:
        yield
    finally:
        logger.info("application_stopping", extra={"service": settings.service_name})


def create_app() -> FastAPI:
    """Build and configure the CivicOs API application."""

    settings = get_settings()
    configure_logging(settings.log_level)

    application = FastAPI(
        title=settings.service_name,
        version=settings.service_version,
        description="RAG-based government document assistant API.",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/health/ready")
    async def readiness() -> dict[str, str]:
        return {"status": "ok"}

    application.include_router(api_router)
    return application




# Avoid creating the FastAPI app at import time during pytest runs to prevent
# startup-side effects (like environment validation) from firing when tests
# import `validate_required_environment` directly.
if os.getenv("PYTEST_CURRENT_TEST") is None:
    app = create_app()
else:
    app = None
