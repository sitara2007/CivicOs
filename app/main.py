"""FastAPI application entrypoint for CivicOs."""

from __future__ import annotations

import logging
import os  # Added to check environment variables
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import create_database_engine
from app.core.logging import configure_logging
from app.db.base import Base
from app.services.observability import configure_telemetry, telemetry

# Setup Logger
logger = logging.getLogger("app.main")


async def create_tables_on_startup() -> None:
    """Initialize database tables automatically on application startup."""
    settings = get_settings()
    if not settings.database_enabled:
        logger.info("Database persistence is disabled; skipping table creation")
        return

    try:
        engine = create_database_engine()
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as exc:  # pragma: no cover - defensive startup path
        logger.warning("Database table initialization skipped: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown concerns."""
    # 1. Initialize Telemetry safely
    if os.getenv("OTEL_SDK_DISABLED", "false").lower() == "true":
        logger.warning("Telemetry is disabled via OTEL_SDK_DISABLED environment variable.")
    else:
        try:
            configure_telemetry(service_name="civicos-api")
            logger.info("Telemetry successfully initialized.")
        except Exception as e:
            # Catching the connection error gracefully so Uvicorn doesn't abort
            logger.error(
                f"Failed to initialize Telemetry backend (likely offline): {e}. "
                "Application will proceed without distributed tracing."
            )

    # 2. Validate Config
    settings = get_settings()
    logger.info("application_starting", extra={"service": settings.service_name})
    app.state.settings = settings

    await create_tables_on_startup()

    yield
    # Shutdown logic
    logger.info("application_stopping", extra={"service": settings.service_name})


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    application = FastAPI(
        title=settings.service_name,
        version=settings.service_version,
        lifespan=lifespan,
    )

    # Middleware: Distributed Tracing (Wrapped in a try/except or telemetry active check if needed)
    @application.middleware("http")
    async def add_trace_id(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        incoming_trace_id = request.headers.get("X-Trace-ID")
        if incoming_trace_id:
            trace_id = incoming_trace_id
        else:
            trace_id = uuid.uuid4().hex

        # If telemetry failed to start, handle trace binding safely
        try:
            telemetry.bind_trace_id(trace_id)
            async with telemetry.span("http_request", {"path": request.url.path}):
                response = await call_next(request)
                response.headers["X-Trace-ID"] = trace_id
                return response
        except Exception:
            # Fallback if telemetry background engine is failing/throwing on middleware
            response = await call_next(request)
            response.headers["X-Trace-ID"] = trace_id
            return response

    # Global Exception Handler (Bulletproof)
    @application.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Critical System Failure: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal error. Trace ID available in logs."},
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
