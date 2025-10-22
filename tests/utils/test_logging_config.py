#!/usr/bin/env python3
"""
Tests for structured logging configuration.
"""

import json
import logging
from io import StringIO
from unittest.mock import patch

import pytest

from lazyscan.utils.logging_config import (
    ConsoleFormatter,
    StructuredFormatter,
    configure_logging,
    get_console_adapter,
    get_logger,
    log_with_context,
)


class TestStructuredFormatter:
    """Test StructuredFormatter for JSON output."""

    def test_basic_json_formatting(self):
        """Test basic JSON formatting of log records."""
        formatter = StructuredFormatter()

        logger = logging.getLogger("test")
        record = logger.makeRecord(
            name="test.module",
            level=logging.INFO,
            fn="test.py",
            lno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert data["level"] == "INFO"
        assert data["logger"] == "test.module"
        assert data["message"] == "Test message"
        assert data["line"] == 42
        assert "timestamp" in data

    def test_extra_fields_included(self):
        """Test that extra fields are included in JSON output."""
        formatter = StructuredFormatter()

        logger = logging.getLogger("test")
        record = logger.makeRecord(
            name="test.module",
            level=logging.INFO,
            fn="test.py",
            lno=42,
            msg="Test with extras",
            args=(),
            exc_info=None,
        )

        # Add extra attributes
        record.path = "/tmp/test"
        record.operation = "delete"
        record.dry_run = True

        result = formatter.format(record)
        data = json.loads(result)

        assert data["path"] == "/tmp/test"
        assert data["operation"] == "delete"
        assert data["dry_run"] is True


class TestConsoleFormatter:
    """Test ConsoleFormatter for human-readable output."""

    def test_basic_console_formatting(self):
        """Test basic console formatting."""
        formatter = ConsoleFormatter(use_colors=False)

        logger = logging.getLogger("test")
        record = logger.makeRecord(
            name="test.module",
            level=logging.INFO,
            fn="test.py",
            lno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)

        assert "[INFO    ]" in result
        assert "test.module" in result
        assert "Test message" in result

    def test_console_extra_fields(self):
        """Test that extra fields are shown in console output."""
        formatter = ConsoleFormatter(use_colors=False)

        logger = logging.getLogger("test")
        record = logger.makeRecord(
            name="test.module",
            level=logging.INFO,
            fn="test.py",
            lno=42,
            msg="Test with extras",
            args=(),
            exc_info=None,
        )

        # Add extra attributes
        record.path = "/tmp/test"
        record.operation = "delete"

        result = formatter.format(record)

        assert "path=/tmp/test" in result
        assert "operation=delete" in result


class TestLoggingConfiguration:
    """Test logging configuration functions."""

    def test_configure_logging_console(self):
        """Test console logging configuration."""
        # Capture stderr to verify handler setup
        with patch("sys.stderr", new_callable=StringIO):
            configure_logging(level="DEBUG", format_type="console")

            logger = get_logger("test.config")

            # Should be at DEBUG level
            assert logger.isEnabledFor(logging.DEBUG)

    def test_configure_logging_json(self):
        """Test JSON logging configuration."""
        with patch("sys.stderr", new_callable=StringIO):
            configure_logging(level="INFO", format_type="json")

            logger = get_logger("test.json")
            assert logger.isEnabledFor(logging.INFO)

    def test_get_logger_returns_logger(self):
        """Test that get_logger returns proper Logger instance."""
        logger = get_logger("test.logger")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.logger"


class TestLogContext:
    """Test structured context logging."""

    def test_context_manager_adds_context(self):
        """Test that context manager properly adds context to logs."""
        logger = get_logger("test.context")

        # Capture log output
        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            configure_logging(level="INFO", format_type="console")

            with log_with_context(logger, operation="test", path="/tmp/test"):
                logger.info("Message with context")

            output = mock_stderr.getvalue()
            assert "operation=test" in output
            assert "path=/tmp/test" in output

    def test_context_restored_after_exit(self):
        """Test that original logger methods are restored after context exit."""
        logger = get_logger("test.restore")
        original_info = logger.info

        with log_with_context(logger, test="value"):
            # Logger method should be different
            assert logger.info != original_info

        # Should be restored
        assert logger.info == original_info


class TestConsoleAdapter:
    """Test ConsoleAdapter functionality."""

    def test_console_adapter_methods(self):
        """Test that console adapter methods work."""
        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            configure_logging(level="INFO", format_type="console")

            adapter = get_console_adapter("test.adapter")

            adapter.print_info("Info message")
            adapter.print_warning("Warning message")
            adapter.print_success("Success message")

            output = mock_stderr.getvalue()
            assert "Info message" in output
            assert "Warning message" in output
            assert "✅ Success message" in output

    def test_console_adapter_with_context(self):
        """Test console adapter with extra context."""
        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            configure_logging(level="INFO", format_type="console")

            adapter = get_console_adapter("test.context")
            adapter.print_info(
                "Message with context", path="/tmp/test", operation="scan"
            )

            output = mock_stderr.getvalue()
            assert "path=/tmp/test" in output
            assert "operation=scan" in output


class TestLoggingLevels:
    """Test logging level behavior."""

    def test_debug_level_shows_debug(self):
        """Test that DEBUG level shows debug messages."""
        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            configure_logging(level="DEBUG", format_type="console")

            logger = get_logger("test.debug")
            logger.debug("Debug message")
            logger.info("Info message")

            output = mock_stderr.getvalue()
            assert "Debug message" in output
            assert "Info message" in output

    def test_info_level_hides_debug(self):
        """Test that INFO level hides debug messages."""
        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            configure_logging(level="INFO", format_type="console")

            logger = get_logger("test.info")
            logger.debug("Debug message")  # Should not appear
            logger.info("Info message")  # Should appear

            output = mock_stderr.getvalue()
            assert "Debug message" not in output
            assert "Info message" in output


if __name__ == "__main__":
    pytest.main([__file__])
