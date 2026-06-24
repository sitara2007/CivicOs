"""Structured logging configuration for the API process."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


_RESERVED_LOG_ATTRS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}

_JSON_HANDLER_MARKER = "_civicos_json_handler"


class JsonFormatter(logging.Formatter):
    """Render log records as compact JSON for machines and humans."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key not in _RESERVED_LOG_ATTRS and not key.startswith("_"):
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str, separators=(",", ":"))


def _normalize_log_level(log_level: str | int) -> int:
    if isinstance(log_level, int):
        return log_level

    if isinstance(log_level, str):
        normalized = log_level.strip().upper()
        if normalized in logging._nameToLevel:
            return logging._nameToLevel[normalized]
        if normalized.isdigit():
            return int(normalized)

    return logging.INFO


def configure_logging(log_level: str = "INFO") -> None:
    """Configure root logging once for JSON stdout output."""

    root_logger = logging.getLogger()
    root_logger.setLevel(_normalize_log_level(log_level))

    root_logger.handlers = [
        handler
        for handler in root_logger.handlers
        if not getattr(handler, _JSON_HANDLER_MARKER, False)
    ]

    handler = logging.StreamHandler(sys.stdout)
    setattr(handler, _JSON_HANDLER_MARKER, True)
    handler.setFormatter(JsonFormatter())
    root_logger.addHandler(handler)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
