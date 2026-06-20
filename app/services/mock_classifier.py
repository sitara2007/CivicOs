"""Deterministic classifier for local dev and CI when MOCK_LLM=true."""

from __future__ import annotations

from app.schemas.process import DecisionOutput, DocumentCategory, Priority

_RULES: list[tuple[tuple[str, ...], DecisionOutput]] = [
    (
        ("pothole", "damaged", "complaint", "burst", "flooding", "emergency"),
        DecisionOutput(
            category=DocumentCategory.COMPLAINT,
            priority=Priority.HIGH,
            department="Public Works",
            confidence=0.91,
            decision_rationale=(
                "Document describes infrastructure damage or service failure requiring "
                "urgent departmental response."
            ),
            summary="Citizen complaint about infrastructure issue routed to Public Works.",
        ),
    ),
    (
        ("request", "copy of", "permit", "application", "records", "assessment"),
        DecisionOutput(
            category=DocumentCategory.REQUEST,
            priority=Priority.LOW,
            department="Tax Assessor",
            confidence=0.89,
            decision_rationale=(
                "Document requests records, permits, or official information from the agency."
            ),
            summary="Citizen request for official records routed to appropriate department.",
        ),
    ),
    (
        ("report", "monthly", "quality", "parameters", "epa", "compliance"),
        DecisionOutput(
            category=DocumentCategory.REPORT,
            priority=Priority.LOW,
            department="Water Utilities",
            confidence=0.93,
            decision_rationale=(
                "Document presents factual reporting data or compliance metrics for review."
            ),
            summary="Official report document routed to Water Utilities for filing.",
        ),
    ),
]


def classify_mock(redacted_text: str) -> DecisionOutput:
    """Keyword-based classifier — satisfies Phase 2 offline demo requirement."""
    lower = redacted_text.lower()

    if any(k in lower for k in ("water main", "burst", "flooding", "basement")):
        return DecisionOutput(
            category=DocumentCategory.COMPLAINT,
            priority=Priority.CRITICAL,
            department="Water Utilities",
            confidence=0.94,
            decision_rationale="Emergency water infrastructure failure requiring immediate response.",
            summary="Critical water main complaint routed to Water Utilities.",
        )

    if "permit" in lower and "renovat" in lower:
        return DecisionOutput(
            category=DocumentCategory.REQUEST,
            priority=Priority.MEDIUM,
            department="Building Permits",
            confidence=0.88,
            decision_rationale="Permit application request for building renovation.",
            summary="Building permit request routed to Building Permits.",
        )

    for keywords, decision in _RULES:
        if any(k in lower for k in keywords):
            return decision

    return DecisionOutput(
        category=DocumentCategory.OTHER,
        priority=Priority.MEDIUM,
        department="General Intake",
        confidence=0.70,
        decision_rationale="Document does not match a specialized category; routed to general intake.",
        summary="Unclassified document sent to General Intake for manual review.",
    )
