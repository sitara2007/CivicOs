"""Backward-compatible settings import.

New code should import ``get_settings`` from ``app.core.config``.
"""

from app.core.config import Settings, get_settings

settings: Settings = get_settings()
