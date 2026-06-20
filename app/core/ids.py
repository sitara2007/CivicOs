"""UUIDv7 generation — PRD §8 trace_id requirement."""

from __future__ import annotations

import uuid


def new_uuid7() -> uuid.UUID:
    """Return a time-sortable UUIDv7 (Python 3.12+ native, uuid6 fallback)."""
    if hasattr(uuid, "uuid7"):
        return uuid.uuid7()
    from uuid6 import uuid7

    return uuid7()
