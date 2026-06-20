"""Text normalization and token pre-flight — FR-1.4, AR-03."""

from __future__ import annotations

import re


def estimate_tokens(text: str) -> int:
    """Rough token estimate (4 chars ≈ 1 token)."""
    return max(1, len(text) // 4)


def normalize_text(text: str) -> str:
    """Collapse excessive whitespace; strip control characters."""
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    return re.sub(r"\s+", " ", cleaned).strip()


def enforce_token_limit(text: str, max_tokens: int = 10_000) -> str:
    """Reject or truncate text exceeding the PRD token ceiling."""
    tokens = estimate_tokens(text)
    if tokens <= max_tokens:
        return text
    char_limit = max_tokens * 4
    return text[:char_limit]
