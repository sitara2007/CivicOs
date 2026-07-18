"""Database helpers for initializing the async engine and session factory."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


def create_database_engine() -> AsyncEngine:
    """Create the async SQLAlchemy engine from application settings."""
    settings = get_settings()
    return create_async_engine(settings.database_url, echo=settings.environment == "development")


def create_async_session_factory() -> async_sessionmaker[AsyncSession]:
    """Build the async session factory used by the app."""
    engine = create_database_engine()
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession | None, None]:
    """Yield a database session for dependency injection."""
    settings = get_settings()
    if not settings.database_enabled:
        yield None
        return

    session_factory = create_async_session_factory()
    async with session_factory() as session:
        yield session
