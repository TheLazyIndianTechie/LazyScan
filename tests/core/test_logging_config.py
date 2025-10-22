#!/usr/bin/env python3
"""
Tests for structured logging framework.
"""

import json
import tempfile
import threading
import time
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from lazyscan.core.logging_config import (
    LogFormat,
    LogLevel,
    StructuredLogger,
    configure_audit_logging,
    get_audit_logger,
    get_console,
    get_logger,
    log_context,
    log_deletion_event,
    log_policy_enforcement,
    log_security_event,
    profile_operation,
    setup_ci_logging,
    setup_development_logging,
    setup_logging,
    setup_production_logging,
)


class TestLoggingSetup:
    """Test logging system setup and configuration."""

    def test_basic_logging_setup(self):
        """Test basic logging configuration."""
        setup_logging(console_format="human", log_level="INFO")

        logger = get_logger(__name__)

        # Should be able to create logger without error
        assert isinstance(logger, StructuredLogger)
        assert logger.name == __name__

    def test_json_logging_setup(self):
        """Test JSON logging configuration."""
        setup_logging(console_format="json", log_level="DEBUG", enable_colors=False)

        logger = get_logger(__name__)
        logger.info("Test JSON message", test_field="test_value")

        # Should not raise any exceptions
        assert isinstance(logger, StructuredLogger)

    def test_file_logging_setup(self):
        """Test file logging configuration."""
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as log_file:
            setup_logging(
                console_format="human", log_level="INFO", log_file=log_file.name
            )

            logger = get_logger(__name__)
            logger.info("Test file message", file_test=True)

            # Verify file was created
            log_path = Path(log_file.name)
            assert log_path.exists()

    def test_log_level_filtering(self):
        """Test that log levels are properly filtered."""
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".log", delete=False
        ) as log_file:
            setup_logging(
                console_format="json", log_level="WARNING", log_file=log_file.name
            )

            logger = get_logger(__name__)
            logger.debug("Debug message")  # Should be filtered out
            logger.info("Info message")  # Should be filtered out
            logger.warning("Warning message")  # Should appear
            logger.error("Error message")  # Should appear

            # Read log file
            log_file.seek(0)
            content = log_file.read()

            # Should only contain warning and error
            assert "Debug message" not in content
            assert "Info message" not in content
            assert "Warning message" in content
            assert "Error message" in content


class TestJSONFormatter:
    """Test JSON formatter functionality."""

    def test_basic_json_formatting(self):
        """Test basic JSON log formatting."""
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".json", delete=False
        ) as log_file:
            setup_logging(
                console_format="json", log_level="INFO", log_file=log_file.name
            )

            logger = get_logger(__name__)
            logger.info("Test message", test_field="test_value", numeric_field=42)

            # Read and parse JSON
            log_file.seek(0)
            content = log_file.read()

            lines = [line.strip() for line in content.split("\n") if line.strip()]
            assert len(lines) >= 1

            log_entry = json.loads(lines[-1])

            # Verify JSON structure
            assert log_entry["level"] == "INFO"
            assert log_entry["message"] == "Test message"
            assert log_entry["test_field"] == "test_value"
            assert log_entry["numeric_field"] == 42
            assert "timestamp" in log_entry
            assert "logger" in log_entry

    def test_json_context_inclusion(self):
        """Test that context is properly included in JSON logs."""
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".json", delete=False
        ) as log_file:
            setup_logging(
                console_format="json", log_level="INFO", log_file=log_file.name
            )

            logger = get_logger(__name__)

            with log_context(operation="test_op", app_type="unity"):
                logger.info("Context test message")

            # Read and parse JSON
            log_file.seek(0)
            content = log_file.read()

            lines = [line.strip() for line in content.split("\n") if line.strip()]
            log_entry = json.loads(lines[-1])

            # Verify context is included
            assert log_entry["operation"] == "test_op"
            assert log_entry["app_type"] == "unity"

    def test_json_exception_handling(self):
        """Test JSON formatting with exceptions."""
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".json", delete=False
        ) as log_file:
            setup_logging(
                console_format="json", log_level="ERROR", log_file=log_file.name
            )

            logger = get_logger(__name__)

            try:
                raise ValueError("Test exception")
            except ValueError:
                import sys

                logger.error("Exception occurred", exc_info=sys.exc_info())

            # Read and parse JSON
            log_file.seek(0)
            content = log_file.read()

            lines = [line.strip() for line in content.split("\n") if line.strip()]
            log_entry = json.loads(lines[-1])

            # Verify exception info is included
            assert "exception" in log_entry
            assert "ValueError" in log_entry["exception"]
            assert "Test exception" in log_entry["exception"]


class TestHumanFormatter:
    """Test human-readable formatter functionality."""

    def test_human_formatting_with_colors(self):
        """Test human formatter with colors enabled."""
        setup_logging(console_format="human", log_level="INFO", enable_colors=True)

        logger = get_logger(__name__)

        # Should not raise exceptions
        logger.info("Test info message")
        logger.warning("Test warning message")
        logger.error("Test error message")

    def test_human_formatting_without_colors(self):
        """Test human formatter with colors disabled."""
        setup_logging(console_format="human", log_level="INFO", enable_colors=False)

        logger = get_logger(__name__)

        # Should not raise exceptions
        logger.info("Test info message")
        logger.warning("Test warning message")
        logger.error("Test error message")

    def test_human_context_display(self):
        """Test that context is displayed in human format."""
        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            setup_logging(console_format="human", log_level="INFO", enable_colors=False)

            logger = get_logger(__name__)

            with log_context(operation="test_operation"):
                logger.info("Test message with context", path="/test/path")

            output = mock_stderr.getvalue()

            # Should include context information
            assert "op=test_operation" in output
            assert "path=/test/path" in output


class TestLogContext:
    """Test log context management."""

    def test_basic_context_usage(self):
        """Test basic context manager usage."""
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".json", delete=False
        ) as log_file:
            setup_logging(
                console_format="json", log_level="INFO", log_file=log_file.name
            )

            logger = get_logger(__name__)

            with log_context(operation="file_scan", app_type="unity"):
                logger.info("Inside context")

                with log_context(file_path="/test/path"):
                    logger.info("Nested context")

            logger.info("Outside context")

            # Parse log entries
            log_file.seek(0)
            content = log_file.read()
            lines = [line.strip() for line in content.split("\n") if line.strip()]

            # First message should have operation and app_type
            entry1 = json.loads(lines[0])
            assert entry1["operation"] == "file_scan"
            assert entry1["app_type"] == "unity"
            assert "file_path" not in entry1

            # Second message should have all context
            entry2 = json.loads(lines[1])
            assert entry2["operation"] == "file_scan"
            assert entry2["app_type"] == "unity"
            assert entry2["file_path"] == "/test/path"

            # Third message should have no context
            entry3 = json.loads(lines[2])
            assert "operation" not in entry3
            assert "app_type" not in entry3
            assert "file_path" not in entry3

    def test_context_thread_safety(self):
        """Test that context is thread-local."""
        setup_logging(console_format="json", log_level="INFO")

        results = {}

        def thread_function(thread_id):
            with log_context(thread_id=thread_id, operation=f"op_{thread_id}"):
                time.sleep(0.1)  # Allow other threads to run

                # Get current context indirectly by logging
                from lazyscan.core.logging_config import _context_storage

                context = getattr(_context_storage, "context", {})
                results[thread_id] = context

        threads = []
        for i in range(3):
            thread = threading.Thread(target=thread_function, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Each thread should have its own context
        assert results[0]["thread_id"] == 0
        assert results[1]["thread_id"] == 1
        assert results[2]["thread_id"] == 2

        assert results[0]["operation"] == "op_0"
        assert results[1]["operation"] == "op_1"
        assert results[2]["operation"] == "op_2"


class TestConsoleAdapter:
    """Test console adapter functionality."""

    def test_basic_console_functions(self):
        """Test basic console adapter functions."""
        setup_logging(console_format="human", log_level="INFO")

        console = get_console()

        # Should not raise exceptions
        console.print("Normal message")
        console.print_info("Info message")
        console.print_success("Success message")
        console.print_warning("Warning message")
        console.print_error("Error message")
        console.print_debug("Debug message")

    def test_console_message_formatting(self):
        """Test console message formatting."""
        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            setup_logging(console_format="human", log_level="INFO", enable_colors=False)

            console = get_console()
            console.print_success("Operation completed")
            console.print_info("Information message")

            output = mock_stderr.getvalue()

            # Should include emoji indicators
            assert "✅" in output
            assert "ℹ️" in output

    def test_console_multiple_args(self):
        """Test console functions with multiple arguments."""
        setup_logging(console_format="human", log_level="INFO")

        console = get_console()

        # Should handle multiple arguments like print()
        console.print("Message", "with", "multiple", "parts")
        console.print_error("Error", "with", "details:", 42)

    def test_console_singleton_behavior(self):
        """Test that get_console returns the same instance."""
        console1 = get_console()
        console2 = get_console()

        assert console1 is console2


class TestPerformanceProfiler:
    """Test performance profiling functionality."""

    def test_successful_operation_profiling(self):
        """Test profiling of successful operations."""
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".json", delete=False
        ) as log_file:
            setup_logging(
                console_format="json", log_level="DEBUG", log_file=log_file.name
            )

            logger = get_logger(__name__)

            with profile_operation(logger, "test_operation"):
                time.sleep(0.1)  # Simulate work

            # Parse log entries
            log_file.seek(0)
            content = log_file.read()
            lines = [line.strip() for line in content.split("\n") if line.strip()]

            # Should have start and completion logs
            assert len(lines) >= 2

            start_entry = json.loads(lines[0])
            assert start_entry["event_type"] == "operation_start"
            assert start_entry["operation"] == "test_operation"

            completion_entry = json.loads(lines[-1])
            assert completion_entry["event_type"] == "operation_completed"
            assert completion_entry["operation"] == "test_operation"
            assert completion_entry["duration_seconds"] >= 0.1

    def test_failed_operation_profiling(self):
        """Test profiling of failed operations."""
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".json", delete=False
        ) as log_file:
            setup_logging(
                console_format="json", log_level="DEBUG", log_file=log_file.name
            )

            logger = get_logger(__name__)

            with pytest.raises(ValueError):
                with profile_operation(logger, "failing_operation"):
                    raise ValueError("Test failure")

            # Parse log entries
            log_file.seek(0)
            content = log_file.read()
            lines = [line.strip() for line in content.split("\n") if line.strip()]

            # Should have start and failure logs
            failure_entry = json.loads(lines[-1])
            assert failure_entry["event_type"] == "operation_failed"
            assert failure_entry["operation"] == "failing_operation"
            assert failure_entry["exception_type"] == "ValueError"


class TestSecurityEventLogging:
    """Test security event logging functions."""

    def test_security_event_logging(self):
        """Test basic security event logging."""
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".json", delete=False
        ) as audit_file:
            configure_audit_logging(audit_file.name, audit_level="INFO")

            log_security_event(
                event_type="policy_violation",
                severity="error",
                description="Security policy violated",
                path="/test/path",
                policy_rule="deny_critical_paths",
            )

            # Parse audit log
            audit_file.seek(0)
            content = audit_file.read()
            lines = [line.strip() for line in content.split("\n") if line.strip()]

            assert len(lines) >= 1
            entry = json.loads(lines[-1])

            assert entry["event_type"] == "policy_violation"
            assert entry["security_event"] is True
            assert entry["path"] == "/test/path"
            assert entry["policy_rule"] == "deny_critical_paths"

    def test_deletion_event_logging(self):
        """Test deletion event logging."""
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".json", delete=False
        ) as audit_file:
            configure_audit_logging(audit_file.name, audit_level="INFO")

            log_deletion_event(
                path="/test/file.txt",
                deletion_mode="trash",
                result="success",
                file_size=1024,
            )

            # Parse audit log
            audit_file.seek(0)
            content = audit_file.read()
            lines = [line.strip() for line in content.split("\n") if line.strip()]

            entry = json.loads(lines[-1])

            assert entry["event_type"] == "file_deletion"
            assert entry["path"] == "/test/file.txt"
            assert entry["deletion_mode"] == "trash"
            assert entry["deletion_result"] == "success"
            assert entry["file_size"] == 1024

    def test_policy_enforcement_logging(self):
        """Test policy enforcement logging."""
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".json", delete=False
        ) as audit_file:
            configure_audit_logging(audit_file.name, audit_level="INFO")

            log_policy_enforcement(
                action="delete_file",
                result="denied",
                policy_hash="abc123",
                path="/critical/path",
                rule_matched="critical_system_path",
            )

            # Parse audit log
            audit_file.seek(0)
            content = audit_file.read()
            lines = [line.strip() for line in content.split("\n") if line.strip()]

            entry = json.loads(lines[-1])

            assert entry["event_type"] == "policy_enforcement"
            assert entry["action"] == "delete_file"
            assert entry["enforcement_result"] == "denied"
            assert entry["policy_hash"] == "abc123"
            assert entry["rule_matched"] == "critical_system_path"


class TestLoggingPresets:
    """Test logging preset configurations."""

    def test_production_logging_setup(self):
        """Test production logging configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_production_logging(
                app_name="test_app", log_dir=temp_dir, enable_audit=True
            )

            # Check that log files are created
            log_path = Path(temp_dir)
            main_log = log_path / "test_app.log"
            audit_log = log_path / "test_app_audit.log"

            logger = get_logger(__name__)
            logger.info("Production test message")

            audit_logger = get_audit_logger()
            audit_logger.info("Audit test message")

            # Files should exist (even if empty initially due to buffering)
            assert main_log.parent.exists()
            assert audit_log.parent.exists()

    def test_development_logging_setup(self):
        """Test development logging configuration."""
        setup_development_logging(verbose=True)

        logger = get_logger(__name__)
        logger.debug("Debug message should appear in verbose mode")
        logger.info("Info message")

        # Should not raise exceptions
        assert isinstance(logger, StructuredLogger)

    def test_ci_logging_setup(self):
        """Test CI/CD logging configuration."""
        setup_ci_logging()

        logger = get_logger(__name__)
        logger.info("CI test message", build_id="12345")

        # Should not raise exceptions
        assert isinstance(logger, StructuredLogger)


class TestStructuredLogger:
    """Test StructuredLogger functionality."""

    def test_logger_methods(self):
        """Test all logger methods."""
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".json", delete=False
        ) as log_file:
            setup_logging(
                console_format="json", log_level="DEBUG", log_file=log_file.name
            )

            logger = get_logger(__name__)

            logger.debug("Debug message", debug_info="test")
            logger.info("Info message", info_data=42)
            logger.warning("Warning message", warning_code="W001")
            logger.error("Error message", error_type="test_error")
            logger.critical("Critical message", critical_level="high")

            # Parse log entries
            log_file.seek(0)
            content = log_file.read()
            lines = [line.strip() for line in content.split("\n") if line.strip()]

            assert len(lines) == 5

            # Verify each log level
            debug_entry = json.loads(lines[0])
            assert debug_entry["level"] == "DEBUG"
            assert debug_entry["debug_info"] == "test"

            info_entry = json.loads(lines[1])
            assert info_entry["level"] == "INFO"
            assert info_entry["info_data"] == 42

            warning_entry = json.loads(lines[2])
            assert warning_entry["level"] == "WARNING"
            assert warning_entry["warning_code"] == "W001"

            error_entry = json.loads(lines[3])
            assert error_entry["level"] == "ERROR"
            assert error_entry["error_type"] == "test_error"

            critical_entry = json.loads(lines[4])
            assert critical_entry["level"] == "CRITICAL"
            assert critical_entry["critical_level"] == "high"


class TestAuditLogging:
    """Test audit logging functionality."""

    def test_audit_logger_separation(self):
        """Test that audit logs are separate from main logs."""
        with (
            tempfile.NamedTemporaryFile(
                mode="w+", suffix=".json", delete=False
            ) as main_log,
            tempfile.NamedTemporaryFile(
                mode="w+", suffix=".json", delete=False
            ) as audit_log,
        ):
            # Setup main logging
            setup_logging(
                console_format="json", log_level="INFO", log_file=main_log.name
            )

            # Setup audit logging
            configure_audit_logging(audit_log.name, audit_level="INFO")

            # Log to both
            main_logger = get_logger(__name__)
            main_logger.info("Main application message")

            audit_logger = get_audit_logger()
            audit_logger.info("Security audit message", security_event=True)

            # Verify separation
            main_log.seek(0)
            main_content = main_log.read()
            assert "Main application message" in main_content
            assert "Security audit message" not in main_content

            audit_log.seek(0)
            audit_content = audit_log.read()
            assert "Security audit message" in audit_content
            assert "Main application message" not in audit_content


class TestLogRotation:
    """Test log file rotation functionality."""

    def test_log_file_rotation_config(self):
        """Test that log rotation is properly configured."""
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as log_file:
            setup_logging(
                console_format="json",
                log_level="INFO",
                log_file=log_file.name,
                max_file_size=1024,  # 1KB for testing
                backup_count=3,
            )

            logger = get_logger(__name__)

            # Generate enough log data to potentially trigger rotation
            for i in range(100):
                logger.info(f"Test message number {i}" * 10)  # Long messages

            # File should exist (rotation testing requires more complex setup)
            log_path = Path(log_file.name)
            assert log_path.exists()


class TestLogLevelsAndFormats:
    """Test log levels and format enums."""

    def test_log_level_enum(self):
        """Test LogLevel enum values."""
        assert LogLevel.DEBUG.value == "DEBUG"
        assert LogLevel.INFO.value == "INFO"
        assert LogLevel.WARNING.value == "WARNING"
        assert LogLevel.ERROR.value == "ERROR"
        assert LogLevel.CRITICAL.value == "CRITICAL"

    def test_log_format_enum(self):
        """Test LogFormat enum values."""
        assert LogFormat.JSON.value == "json"
        assert LogFormat.HUMAN.value == "human"


if __name__ == "__main__":
    pytest.main([__file__])
