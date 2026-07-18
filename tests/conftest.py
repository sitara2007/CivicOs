"""Shared pytest fixtures — disable DB by default for unit tests."""

from __future__ import annotations

import pytest

from app.core.config import get_settings


@pytest.fixture(autouse=True)
def test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_ENABLED", "false")
    monkeypatch.setenv("MOCK_LLM", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()
