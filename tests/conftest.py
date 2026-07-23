"""Pytest configuration and global fixtures for CivicOs."""
from __future__ import annotations

import os

os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5432/civicos"
import pytest
from app.core.config import get_settings  # noqa: E402
@pytest.fixture(autouse=True)
def test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_ENABLED", "false")
    monkeypatch.setenv("MOCK_LLM", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()
