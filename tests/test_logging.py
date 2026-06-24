import logging

from app.core.logging import _normalize_log_level


def test_normalize_log_level_supports_named_levels() -> None:
    assert _normalize_log_level("DEBUG") == logging.DEBUG
    assert _normalize_log_level("info") == logging.INFO


def test_normalize_log_level_falls_back_to_info_for_unknown_values() -> None:
    assert _normalize_log_level("not-a-level") == logging.INFO
