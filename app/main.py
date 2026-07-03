"""FastAPI application entrypoint for CivicOs."""
from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.services.observability import configure_telemetry, telemetry

# Setup Logger
logger = logging.getLogger("app.main")

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown concerns."""
    # 1. Initialize Telemetry (Distributed Tracing)
    configure_telemetry(service_name="civicos-api")
    
    # 2. Validate Config
    settings = get_settings()
    logger.info("application_starting", extra={"service": settings.service_name})
    app.state.settings = settings
    
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

    # Middleware: Distributed Tracing
    @application.middleware("http")
    async def add_trace_id(request: Request, call_next):
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
        telemetry.bind_trace_id(trace_id)
        
        async with telemetry.span("http_request", {"path": request.url.path}):
            response = await call_next(request)
            response.headers["X-Trace-ID"] = trace_id
            return response

    # Global Exception Handler (Bulletproof)
    @application.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Critical System Failure: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal error. Trace ID available in logs."}
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