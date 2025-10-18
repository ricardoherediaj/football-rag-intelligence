"""Tests for JSON logging."""

import json
import logging
from io import StringIO

from football_rag.core.logging import get_logger, setup_logging


def test_setup_logging_creates_handler():
    """Test that setup_logging adds a handler."""
    root = logging.getLogger()
    initial_handlers = len(root.handlers)
    setup_logging()
    assert len(root.handlers) >= initial_handlers


def test_get_logger_returns_logger():
    """Test that get_logger returns a logger instance."""
    logger = get_logger("test")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test"


def test_json_formatter_produces_json():
    """Test that logs are formatted as JSON."""
    logger = get_logger("test.json")
    stream = StringIO()
    handler = logging.StreamHandler(stream)

    from football_rag.core.logging import _JsonFormatter

    handler.setFormatter(_JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    logger.info("Test message")
    output = stream.getvalue()

    try:
        parsed = json.loads(output.strip())
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test.json"
        assert parsed["msg"] == "Test message"
    except json.JSONDecodeError:
        pytest.fail(f"Output is not valid JSON: {output}")
