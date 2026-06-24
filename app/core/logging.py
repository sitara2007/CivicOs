"""Structured logging configuration for the API process."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import sys
import sysconfig
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any


def _load_stdlib_logging():
    stdlib_path = sysconfig.get_paths()["stdlib"]
    spec = importlib.machinery.PathFinder.find_spec("logging", [stdlib_path])
    if spec is None or spec.loader is None:
        raise ImportError("Unable to locate the Python standard logging module")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


logging = _load_stdlib_logging()

if TYPE_CHECKING:
    from logging import Formatter as LoggingFormatter
    from logging import LogRecord as LoggingLogRecord
else:
    LoggingFormatter = logging.Formatter
    LoggingLogRecord = logging.LogRecord


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
}


class JsonFormatter(LoggingFormatter):
    """Render log records as compact JSON for machines and humans."""

    def format(self, record: LoggingLogRecord) -> str:
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


def configure_logging(log_level: str = "INFO") -> None:
    """Configure root logging once for JSON stdout output."""

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(log_level.upper())

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root_logger.addHandler(handler)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
