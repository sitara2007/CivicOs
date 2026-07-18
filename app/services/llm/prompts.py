"""Prompt builders for LLM-backed document decisions."""

from __future__ import annotations


def build_classification_messages(
    redacted_text: str, policy_context: str = ""
) -> list[dict[str, str]]:
    context = policy_context.strip() or "No relevant policy context was retrieved."

    system_prompt = (
        "You are an Autonomous Document Architect for government workflows. "
        "Your goal is to classify, sanitize, and route incoming documents with 99.9% accuracy. "
        "Analyze the raw text for core intent, detect PII, assess relevance, and reason through "
        "department and urgency. If the input is ambiguous, recommend manual review rather "
        "than guessing. If a structural error is detected, flag manual_review true immediately. "
        "If confidence_score is below 0.8, use the policy context for clarification. "
        "Return strictly valid JSON only; do not include markdown, comments, or extra text."
    )

    user_prompt = (
        f"Policy context:\n{context}\n\n"
        f"Document:\n{redacted_text}\n\n"
        "Return exactly one JSON object with these keys:\n"
        "classification (department name), category (Complaint|Request|Report|Other), "
        "priority (High|Medium|Low|Critical), pii_detected (true|false), "
        "confidence_score (0.0-1.0), reasoning (brief technical explanation), "
        "manual_review (true|false), summary (short routing summary).\n"
        "Do not invent facts. If the document is informational only, classify it as "
        "Other and keep priority Low."
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
