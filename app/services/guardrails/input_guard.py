from __future__ import annotations

import re
from typing import NamedTuple

PROMPT_INJECTION_PATTERNS = [
    r"(?i)ignore (previous|earlier) instructions",
    r"(?i)disregard (previous|earlier) instructions",
    r"(?i)forget all prior guidance",
    r"(?i)answer.*only",
]

PII_PATTERNS = [
    re.compile(r"\b[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b\d{4} \d{4} \d{4} \d{4}\b"),
    re.compile(r"\b\+?\d{1,3}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{2,4}[-.\s]?\d{2,9}\b"),
]


class InputValidationError(ValueError):
    pass


class GuardResult(NamedTuple):
    text: str
    pii_count: int


class InputGuard:
    def validate(self, text: str) -> None:
        if not text or not text.strip():
            raise InputValidationError("Input text must not be empty")
        if len(text) > 100_000:
            raise InputValidationError("Input text exceeds maximum allowed length")

    def sanitize(self, text: str) -> GuardResult:
        self.validate(text)
        normalized = self._normalize(text)
        filtered = self._filter_prompt_injection(normalized)
        redacted, pii_count = self._filter_pii(filtered)
        return GuardResult(text=redacted, pii_count=pii_count)

    def _normalize(self, text: str) -> str:
        return " ".join(text.split())

    def _filter_prompt_injection(self, text: str) -> str:
        sanitized = text
        for pattern in PROMPT_INJECTION_PATTERNS:
            sanitized = re.sub(pattern, "[REDACTED_INJECTION]", sanitized)
        return sanitized

    def _filter_pii(self, text: str) -> tuple[str, int]:
        total_redactions = 0
        sanitized = text
        for pattern in PII_PATTERNS:
            sanitized, redactions = pattern.subn("[REDACTED]", sanitized)
            total_redactions += redactions
        return sanitized, total_redactions
