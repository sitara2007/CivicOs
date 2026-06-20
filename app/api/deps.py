"""FastAPI dependencies shared by API routes."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_session


async def get_db_session() -> AsyncGenerator[AsyncSession | None, None]:
    """Yield a database session when persistence is enabled."""

    if not get_settings().database_enabled:
        yield None
        return

    async for session in get_session():
        yield session
