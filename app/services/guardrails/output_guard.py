from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.schemas.process import DecisionOutput


class OutputValidationError(ValueError):
    pass


class OutputGuard:
    def validate(self, payload: dict[str, Any]) -> DecisionOutput:
        try:
            decision = DecisionOutput.model_validate(payload)
        except ValidationError as exc:
            raise OutputValidationError(
                "LLM output did not conform to the expected schema"
            ) from exc

        for value in decision.model_dump().values():
            if isinstance(value, str) and self._looks_like_pii(value):
                raise OutputValidationError("LLM output contains possible PII")

        return decision

    @staticmethod
    def _looks_like_pii(value: str) -> bool:
        lower = value.lower()
        return "@" in lower or "ssn" in lower or "social security" in lower or "+1" in lower
