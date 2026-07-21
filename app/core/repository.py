"""Generic repository helpers for application services."""

from __future__ import annotations

from typing import Any, TypeVar

T = TypeVar("T")


class BaseRepository[T]:
    """Minimal repository base with a simple in-memory store interface."""

    def __init__(self) -> None:
        self._store: dict[str, T] = {}

    def add(self, key: str, value: T) -> None:
        self._store[key] = value

    def get(self, key: str) -> T | None:
        return self._store.get(key)

    def list(self) -> list[T]:
        return list(self._store.values())

    def delete(self, key: str) -> None:
        self._store.pop(key, None)


class DocumentRepository(BaseRepository[dict[str, Any]]):
    """Convenience wrapper for storing document-like payloads."""

    def save_document(self, key: str, payload: dict[str, Any]) -> None:
        self.add(key, payload)

    def get_document(self, key: str) -> dict[str, Any] | None:
        return self.get(key)
