"""SQLAlchemy declarative base for app models."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for ORM models and metadata collection."""
