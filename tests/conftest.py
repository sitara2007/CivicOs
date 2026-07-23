"""Pytest configuration and global fixtures for CivicOs."""

from __future__ import annotations

import os

# Set a fallback database URL before any application modules or models load
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/civicos"
)

# Your subsequent pytest fixtures and imports follow here...
"""Shared pytest fixtures — disable DB by default for unit tests."""
from __future__ import annotations  # noqa: E402, F404
import pytest  # noqa: E402
from app.core.config import get_settings  # noqa: E402
@pytest.fixture(autouse=True)
def test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_ENABLED", "false")
    monkeypatch.setenv("MOCK_LLM", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()
