from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from app.core.config import get_settings
from app.services.rag.generator import get_answer


def test_get_answer_builds_prompt_and_returns_model_text() -> None:
    dummy_response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="This is the answer."))]
    )

    mock_chunks = [
        {"text": "First context."},
        {"text": "Second context."},
    ]

    with patch("app.services.rag.generator.retrieve", return_value=mock_chunks) as mock_retrieve, patch(
        "app.services.rag.generator.client.chat.completions.create",
        return_value=dummy_response,
    ) as mock_create:
        answer = get_answer("What is the scheme?")

    assert answer == "This is the answer."
    mock_retrieve.assert_called_once_with("What is the scheme?")
    mock_create.assert_called_once_with(
        model=get_settings().openai_model,
        messages=[
            {
                "role": "user",
                "content": "Use this context to answer the question: First context.\nSecond context.\n\nQuestion: What is the scheme?",
            }
        ],
    )


def test_get_answer_handles_empty_context() -> None:
    dummy_response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="No context available."))]
    )

    with patch("app.services.rag.generator.retrieve", return_value=[]), patch(
        "app.services.rag.generator.client.chat.completions.create",
        return_value=dummy_response,
    ) as mock_create:
        answer = get_answer("What now?")

    assert answer == "No context available."
    mock_create.assert_called_once()
