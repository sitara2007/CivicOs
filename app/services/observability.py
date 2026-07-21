from __future__ import annotations

import contextvars
import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from loguru import logger
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

TRACE_ID = contextvars.ContextVar("trace_id", default="unknown")


def configure_logging(level: str = "INFO") -> None:
    logger.remove()
    logger.add(
        sys.stdout,
        level=level.upper(),
        serialize=True,
        enqueue=True,
        backtrace=False,
        diagnose=False,
    )


def configure_telemetry(service_name: str = "civicos") -> None:
    resource = Resource.create({"service.name": service_name})

    trace_exporter = OTLPSpanExporter(
        endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
    )
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
    trace.set_tracer_provider(tracer_provider)

    metric_exporter = OTLPMetricExporter(
        endpoint=os.getenv("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT", "http://localhost:4318")
    )
    meter_provider = MeterProvider(
        metric_readers=[PeriodicExportingMetricReader(metric_exporter)], resource=resource
    )
    metrics.set_meter_provider(meter_provider)


def current_trace_id() -> str:
    return TRACE_ID.get()


class TelemetryClient:
    def __init__(self) -> None:
        self._tracer = trace.get_tracer(__name__)
        self._meter = metrics.get_meter(__name__)
        self.latency_histogram = self._meter.create_histogram(
            "ai.pipeline.latency_ms",
            description="Latency for end-to-end AI inference flow in milliseconds",
        )
        self.token_counter = self._meter.create_counter(
            "ai.pipeline.tokens",
            description="Token usage recorded for prompt and response pairs",
        )

    @asynccontextmanager
    async def span(
        self, name: str, attributes: dict[str, Any] | None = None
    ) -> AsyncIterator[None]:
        attributes = attributes or {}
        with self._tracer.start_as_current_span(name, attributes=attributes):
            yield

    def bind_trace_id(self, trace_id: str) -> None:
        TRACE_ID.set(trace_id)

    def record_latency(self, latency_ms: float) -> None:
        self.latency_histogram.record(latency_ms, {"trace_id": current_trace_id()})

    def record_tokens(self, prompt_tokens: int, response_tokens: int) -> None:
        self.token_counter.add(prompt_tokens + response_tokens, {"trace_id": current_trace_id()})


telemetry = TelemetryClient()
