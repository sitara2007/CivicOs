"""Microsoft Presidio PII sanitization — FR-1.2, GDPR/HIPAA pre-LLM gate."""

from __future__ import annotations

import logging
import re

import pybreaker

from app.resilience.breakers import presidio_breaker

logger = logging.getLogger(__name__)

ENTITIES = [
    "PERSON",
    "PHONE_NUMBER",
    "US_SSN",
    "EMAIL_ADDRESS",
    "CREDIT_CARD",
    "US_DRIVER_LICENSE",
    "US_PASSPORT",
    "MEDICAL_LICENSE",
    "US_BANK_NUMBER",
]

# Regex fallback when Presidio/spaCy unavailable (dev bootstrap)
_REGEX_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "<US_SSN>"),
    (re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"), "<PHONE_NUMBER>"),
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "<EMAIL_ADDRESS>"),
]


class SanitizationError(Exception):
    """Raised when Presidio is unavailable — fail closed, no LLM call."""


def _regex_fallback(text: str) -> tuple[str, int]:
    redacted = text
    count = 0
    for pattern, replacement in _REGEX_PATTERNS:
        redacted, n = pattern.subn(replacement, redacted)
        count += n
    return redacted, count


def _analyze_and_anonymize(text: str) -> tuple[str, int]:
    try:
        from presidio_analyzer import AnalyzerEngine
        from presidio_anonymizer import AnonymizerEngine

        analyzer = AnalyzerEngine()
        results = analyzer.analyze(text=text, entities=ENTITIES, language="en")
        anonymized = AnonymizerEngine().anonymize(text=text, analyzer_results=results)
        return anonymized.text, len(results)
    except Exception as exc:
        logger.warning("presidio_fallback_to_regex", extra={"error": str(exc)})
        return _regex_fallback(text)


def sanitize(text: str) -> tuple[str, int]:
    """Mask PII before any LLM transmission. Fail closed on circuit open."""
    try:
        return presidio_breaker.call(_analyze_and_anonymize, text)
    except pybreaker.CircuitBreakerError as exc:
        logger.error("presidio_circuit_open")
        raise SanitizationError("Presidio unavailable — refusing LLM pipeline") from exc
