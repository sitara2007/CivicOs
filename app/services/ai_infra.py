from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from loguru import logger
from openai import OpenAI

from app.core.config import get_settings
from app.schemas.process import DecisionOutput, SourceType
from app.services.guardrails.input_guard import (
    InputGuard,
    InputValidationError,
)
from app.services.guardrails.output_guard import OutputGuard, OutputValidationError
from app.services.llm.prompts import build_classification_messages
from app.services.mock_classifier import classify_mock
from app.services.observability import (
    TelemetryClient,
    configure_logging,
    configure_telemetry,
    telemetry,
)
from app.services.rag.retriever import retrieve


class InferenceError(RuntimeError):
    pass


class AIInferenceResult:
    def __init__(
        self,
        decision: DecisionOutput,
        prompt_tokens: int,
        response_tokens: int,
        pii_entities_masked: int,
        latency_ms: float,
    ) -> None:
        self.decision = decision
        self.prompt_tokens = prompt_tokens
        self.response_tokens = response_tokens
        self.pii_entities_masked = pii_entities_masked
        self.latency_ms = latency_ms


class AsyncOpenAIAdapter:
    def __init__(self) -> None:
        self._settings = get_settings()

    async def classify(
        self, redacted_text: str, policy_context: str, trace_id: str
    ) -> tuple[dict[str, Any], int, int]:
        if self._settings.use_mock_llm:
            return classify_mock(redacted_text).model_dump(), 1, 1

        client = OpenAI(api_key=self._settings.openai_api_key)
        messages = build_classification_messages(
            redacted_text=redacted_text, policy_context=policy_context
        )

        def _call() -> tuple[dict[str, Any], int, int]:
            response = client.chat.completions.create(
                model=self._settings.openai_model,
                messages=messages,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            payload = json.loads(content)
            prompt_tokens = getattr(response.usage, "prompt_tokens", 0)
            response_tokens = getattr(response.usage, "completion_tokens", 0)
            return payload, prompt_tokens, response_tokens

        payload, prompt_tokens, response_tokens = await asyncio.to_thread(_call)
        return payload, prompt_tokens, response_tokens


class AsyncQdrantRetriever:
    async def retrieve(self, query: str, top_k: int) -> list[dict[str, Any]]:
        return await asyncio.to_thread(retrieve, query, top_k)


class AIInferenceService:
    def __init__(
        self,
        input_guard: InputGuard | None = None,
        output_guard: OutputGuard | None = None,
        llm_adapter: AsyncOpenAIAdapter | None = None,
        retriever: AsyncQdrantRetriever | None = None,
        telemetry_client: TelemetryClient | None = None,
    ) -> None:
        self._settings = get_settings()
        self._input_guard = input_guard or InputGuard()
        self._output_guard = output_guard or OutputGuard()
        self._llm_adapter = llm_adapter or AsyncOpenAIAdapter()
        self._retriever = retriever or AsyncQdrantRetriever()
        self._telemetry = telemetry_client or telemetry

    async def start(self) -> None:
        configure_logging(self._settings.log_level)
        configure_telemetry(self._settings.service_name)

    async def classify_document(
        self, text: str, source_type: SourceType, trace_id: str
    ) -> AIInferenceResult:
        self._telemetry.bind_trace_id(trace_id)
        bound_logger = logger.bind(trace_id=trace_id, source_type=source_type.value)
        start = time.perf_counter()

        try:
            with await self._telemetry.span("ai.inference", {"source_type": source_type.value}):
                guard_result = self._input_guard.sanitize(text)
                bound_logger.info("input_sanitized", pii_entities_masked=guard_result.pii_count)

                policy_context = ""
                if self._settings.rag_enabled:
                    chunks = await self._retriever.retrieve(
                        guard_result.text, self._settings.rag_top_k
                    )
                    policy_context = "\n\n".join(
                        chunk.get("text", "") for chunk in chunks if chunk.get("text")
                    )

                raw_payload, prompt_tokens, response_tokens = await self._llm_adapter.classify(
                    guard_result.text,
                    policy_context,
                    trace_id,
                )

                decision = self._output_guard.validate(raw_payload)
                latency_ms = (time.perf_counter() - start) * 1000

                self._telemetry.record_latency(latency_ms)
                self._telemetry.record_tokens(prompt_tokens, response_tokens)
                bound_logger.info(
                    "ai_inference_completed",
                    latency_ms=latency_ms,
                    prompt_tokens=prompt_tokens,
                    response_tokens=response_tokens,
                    pii_entities_masked=guard_result.pii_count,
                )

                return AIInferenceResult(
                    decision=decision,
                    prompt_tokens=prompt_tokens,
                    response_tokens=response_tokens,
                    pii_entities_masked=guard_result.pii_count,
                    latency_ms=latency_ms,
                )
        except (InputValidationError, OutputValidationError) as exc:
            bound_logger.warning("ai_inference_validation_failed", error=str(exc))
            raise
        except Exception as exc:
            bound_logger.exception("ai_inference_failed", error=str(exc))
            raise InferenceError("AI inference failed unexpectedly") from exc
