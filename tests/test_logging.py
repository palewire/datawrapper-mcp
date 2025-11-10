"""Tests for logging infrastructure."""

import json
import logging
import os
from unittest.mock import patch


from datawrapper_mcp.logging import (
    JsonFormatter,
    get_correlation_id,
    get_logger,
    log_duration,
    setup_logging,
)


class TestJsonFormatter:
    """Tests for JsonFormatter class."""

    def test_format_basic_record(self):
        """Test formatting a basic log record."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert data["timestamp"]
        assert data["level"] == "INFO"
        assert data["logger"] == "test"
        assert data["message"] == "Test message"

    def test_format_with_extra_fields(self):
        """Test formatting with extra fields."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.correlation_id = "test-123"
        record.chart_id = "abc123"

        result = formatter.format(record)
        data = json.loads(result)

        assert data["correlation_id"] == "test-123"
        assert data["chart_id"] == "abc123"

    def test_format_with_exception(self):
        """Test formatting with exception info."""
        import sys

        formatter = JsonFormatter()
        try:
            raise ValueError("Test error")
        except ValueError:
            exc_info = sys.exc_info()
            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=1,
                msg="Error occurred",
                args=(),
                exc_info=exc_info,
            )

            result = formatter.format(record)
            data = json.loads(result)

            assert data["level"] == "ERROR"
            assert data["message"] == "Error occurred"
            assert "exception" in data
            assert "ValueError: Test error" in data["exception"]


class TestCorrelationId:
    """Tests for correlation ID functionality."""

    def test_get_correlation_id_creates_new(self):
        """Test that get_correlation_id creates a new UUID."""
        corr_id = get_correlation_id()
        assert corr_id
        assert len(corr_id) == 36  # UUID format

    def test_get_correlation_id_returns_same_in_context(self):
        """Test that correlation ID is consistent within context."""
        corr_id1 = get_correlation_id()
        corr_id2 = get_correlation_id()
        assert corr_id1 == corr_id2


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_adds_prefix(self):
        """Test that get_logger adds datawrapper_mcp prefix."""
        logger = get_logger("test")
        assert logger.name == "datawrapper_mcp.test"

    def test_get_logger_returns_logger_instance(self):
        """Test that get_logger returns a Logger instance."""
        logger = get_logger("test")
        assert isinstance(logger, logging.Logger)


class TestLogDuration:
    """Tests for log_duration helper."""

    def test_log_duration_calculates_milliseconds(self):
        """Test that log_duration calculates duration in milliseconds."""
        import time

        start = time.time()
        time.sleep(0.01)  # Sleep for 10ms
        duration = log_duration(start)

        assert duration >= 10
        assert duration < 100  # Should be less than 100ms


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_setup_logging_default_text_format(self):
        """Test setup_logging with default text format."""
        with patch.dict(os.environ, {}, clear=True):
            setup_logging()

            root_logger = logging.getLogger("datawrapper_mcp")
            assert root_logger.level == logging.INFO
            assert len(root_logger.handlers) == 1
            assert isinstance(root_logger.handlers[0], logging.StreamHandler)

    def test_setup_logging_json_format(self):
        """Test setup_logging with JSON format."""
        with patch.dict(
            os.environ,
            {"DATAWRAPPER_MCP_LOG_FORMAT": "json"},
            clear=True,
        ):
            setup_logging()

            root_logger = logging.getLogger("datawrapper_mcp")
            handler = root_logger.handlers[0]
            assert isinstance(handler.formatter, JsonFormatter)

    def test_setup_logging_custom_level(self):
        """Test setup_logging with custom log level."""
        with patch.dict(
            os.environ,
            {"DATAWRAPPER_MCP_LOG_LEVEL": "DEBUG"},
            clear=True,
        ):
            setup_logging()

            root_logger = logging.getLogger("datawrapper_mcp")
            assert root_logger.level == logging.DEBUG

    def test_setup_logging_invalid_level_uses_default(self):
        """Test that invalid log level falls back to INFO."""
        with patch.dict(
            os.environ,
            {"DATAWRAPPER_MCP_LOG_LEVEL": "INVALID"},
            clear=True,
        ):
            setup_logging()

            root_logger = logging.getLogger("datawrapper_mcp")
            assert root_logger.level == logging.INFO

    def test_setup_logging_clears_existing_handlers(self):
        """Test that setup_logging clears existing handlers."""
        root_logger = logging.getLogger("datawrapper_mcp")

        # Add a dummy handler
        dummy_handler = logging.StreamHandler()
        root_logger.addHandler(dummy_handler)
        _initial_count = len(root_logger.handlers)

        setup_logging()

        # Should have exactly 1 handler after setup
        assert len(root_logger.handlers) == 1
        assert dummy_handler not in root_logger.handlers


class TestLoggingIntegration:
    """Integration tests for logging functionality."""

    def test_logger_with_correlation_id(self, caplog):
        """Test that logger includes correlation_id in output."""
        with caplog.at_level(logging.INFO):
            logger = get_logger("test")
            corr_id = get_correlation_id()

            logger.info(
                "Test message",
                extra={"correlation_id": corr_id},
            )

            assert len(caplog.records) == 1
            assert caplog.records[0].correlation_id == corr_id

    def test_logger_with_multiple_extra_fields(self, caplog):
        """Test logger with multiple extra fields."""
        with caplog.at_level(logging.INFO):
            logger = get_logger("test")

            logger.info(
                "Test message",
                extra={
                    "correlation_id": "test-123",
                    "chart_id": "abc123",
                    "chart_type": "bar",
                    "duration_ms": 150,
                },
            )

            assert len(caplog.records) == 1
            record = caplog.records[0]
            assert record.correlation_id == "test-123"
            assert record.chart_id == "abc123"
            assert record.chart_type == "bar"
            assert record.duration_ms == 150
