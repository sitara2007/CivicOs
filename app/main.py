"""FastAPI application entrypoint for CivicOs."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)


def _has_env_value(*names: str) -> bool:
    """Return whether any named environment variable is set to a non-empty value."""

    return any(os.getenv(name, "").strip() for name in names)


def validate_required_environment() -> None:
    """Fail fast when required startup environment variables are missing."""

    settings = get_settings()
    missing: list[str] = []

    if settings.database_enabled and not _has_env_value("POSTGRES_URL", "DATABASE_URL"):
        missing.append("POSTGRES_URL or DATABASE_URL")

    if not settings.use_mock_llm and not _has_env_value("LLM_API_KEY", "OPENAI_API_KEY"):
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

    application.include_router(api_router)
    return application


app = create_app()
