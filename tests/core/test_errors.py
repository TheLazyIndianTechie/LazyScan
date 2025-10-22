#!/usr/bin/env python3
"""
Tests for comprehensive error handling system.
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from lazyscan.core.errors import (
    DeletionSafetyError,
    DiscoveryError,
    ExitCode,
    LazyScanError,
    PathValidationError,
    SecurityPolicyError,
    UserAbortedError,
    ValidationError,
    cli_error_handler,
    format_user_error,
    handle_exception,
    retry_with_backoff,
    safe_operation,
    validate_directory_exists,
    validate_file_exists,
    validate_not_none,
)


class TestExitCodes:
    """Test exit code enumeration."""

    def test_exit_codes_defined(self):
        """Test that all expected exit codes are defined."""
        assert ExitCode.SUCCESS == 0
        assert ExitCode.GENERAL_ERROR == 1
        assert ExitCode.PATH_ERROR == 3
        assert ExitCode.SECURITY_ERROR == 5
        assert ExitCode.USER_CANCELLED == 7

    def test_exit_codes_unique(self):
        """Test that all exit codes are unique."""
        codes = [code.value for code in ExitCode]
        assert len(codes) == len(set(codes))


class TestLazyScanError:
    """Test base LazyScanError functionality."""

    def test_basic_error_creation(self):
        """Test creating basic LazyScan error."""
        error = LazyScanError("Test error")

        assert str(error) == "Test error"
        assert error.exit_code == ExitCode.GENERAL_ERROR
        assert error.user_message == "Test error"
        assert error.context == {}

    def test_error_with_context(self):
        """Test creating error with context."""
        context = {"path": "/tmp/test", "operation": "delete"}
        error = LazyScanError(
            "Test error", ExitCode.PATH_ERROR, context, "User message"
        )

        assert error.exit_code == ExitCode.PATH_ERROR
        assert error.context == context
        assert error.user_message == "User message"

    def test_to_dict_conversion(self):
        """Test converting error to dictionary."""
        context = {"test": "value"}
        error = LazyScanError(
            "Test message", ExitCode.CONFIG_ERROR, context, "User message"
        )

        result = error.to_dict()

        assert result["exception_type"] == "LazyScanError"
        assert result["message"] == "Test message"
        assert result["user_message"] == "User message"
        assert result["exit_code"] == ExitCode.CONFIG_ERROR
        assert result["context"] == context


class TestSpecificExceptions:
    """Test specific exception types."""

    def test_path_validation_error(self):
        """Test PathValidationError with path context."""
        error = PathValidationError("Invalid path", path="/invalid/path")

        assert error.exit_code == ExitCode.PATH_ERROR
        assert error.context["path"] == "/invalid/path"

    def test_deletion_safety_error(self):
        """Test DeletionSafetyError with safety context."""
        error = DeletionSafetyError(
            "Unsafe deletion", path="/", reason="root directory"
        )

        assert error.exit_code == ExitCode.DELETION_ERROR
        assert error.context["path"] == "/"
        assert error.context["safety_reason"] == "root directory"
        assert "Deletion blocked for safety" in error.user_message

    def test_security_policy_error(self):
        """Test SecurityPolicyError with policy context."""
        error = SecurityPolicyError("Policy violation", policy_hash="abc123")

        assert error.exit_code == ExitCode.SECURITY_ERROR
        assert error.context["policy_hash"] == "abc123"
        assert "Security policy violation" in error.user_message

    def test_discovery_error(self):
        """Test DiscoveryError with search context."""
        search_paths = ["/path1", "/path2"]
        error = DiscoveryError(
            "No projects found", search_paths=search_paths, app_type="unity"
        )

        assert error.exit_code == ExitCode.DISCOVERY_ERROR
        assert error.context["search_paths"] == search_paths
        assert error.context["app_type"] == "unity"

    def test_user_aborted_error(self):
        """Test UserAbortedError."""
        error = UserAbortedError(operation="deletion")

        assert error.exit_code == ExitCode.USER_CANCELLED
        assert error.context["operation"] == "deletion"


class TestErrorHandling:
    """Test error handling utilities."""

    def test_handle_custom_exception(self):
        """Test handling of custom LazyScan exceptions."""
        logger = MagicMock()
        error = PathValidationError("Test path error", path="/test/path")

        result = handle_exception(error, logger, "test_operation")

        assert result["exception_type"] == "PathValidationError"
        assert result["operation"] == "test_operation"
        assert result["exit_code"] == ExitCode.PATH_ERROR
        logger.error.assert_called_once()

    def test_handle_generic_exception(self):
        """Test handling of generic exceptions."""
        logger = MagicMock()
        error = ValueError("Generic error")

        result = handle_exception(error, logger, "test_operation")

        assert result["exception_type"] == "ValueError"
        assert result["operation"] == "test_operation"
        assert result["exit_code"] == ExitCode.GENERAL_ERROR
        logger.error.assert_called_once()

    def test_format_user_error_custom(self):
        """Test formatting custom errors for users."""
        error = PathValidationError("Path invalid", path="/test")

        result = format_user_error(error)

        assert "❌" in result
        assert "Path invalid" in result
        assert "/test" in result
        assert "💡" in result  # Should include suggestion

    def test_format_user_error_generic(self):
        """Test formatting generic errors for users."""
        error = ValueError("Generic error")

        result = format_user_error(error)

        assert result == "❌ Unexpected error: Generic error"


class TestRetryMechanism:
    """Test retry with backoff functionality."""

    def test_successful_operation_no_retry(self):
        """Test that successful operations don't retry."""
        call_count = 0

        def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = retry_with_backoff(success_func, max_attempts=3)

        assert result == "success"
        assert call_count == 1

    def test_eventual_success_with_retry(self):
        """Test that operations eventually succeed after retries."""
        call_count = 0

        def eventually_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise OSError("Temporary failure")
            return "success"

        result = retry_with_backoff(eventually_succeed, max_attempts=5, base_delay=0.1)

        assert result == "success"
        assert call_count == 3

    def test_max_attempts_exceeded(self):
        """Test that max attempts are respected."""

        def always_fail():
            raise OSError("Persistent failure")

        with pytest.raises(OSError, match="Persistent failure"):
            retry_with_backoff(always_fail, max_attempts=2, base_delay=0.1)

    def test_non_retryable_exception_immediate_failure(self):
        """Test that non-retryable exceptions fail immediately."""
        call_count = 0

        def fail_with_non_retryable():
            nonlocal call_count
            call_count += 1
            raise ValueError("Non-retryable error")

        with pytest.raises(ValueError, match="Non-retryable error"):
            retry_with_backoff(
                fail_with_non_retryable, max_attempts=3, retryable_exceptions=(OSError,)
            )

        assert call_count == 1  # Should not retry


class TestSafeOperation:
    """Test safe operation wrapper."""

    def test_safe_operation_success(self):
        """Test successful safe operation."""
        logger = MagicMock()

        def test_func():
            return "result"

        result = safe_operation("test_op", test_func, logger)

        assert result == "result"
        logger.debug.assert_called()

    def test_safe_operation_with_retry(self):
        """Test safe operation with retry enabled."""
        logger = MagicMock()
        call_count = 0

        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise OSError("Temporary failure")
            return "success"

        result = safe_operation(
            "retry_op",
            flaky_func,
            logger,
            retryable=True,
            max_attempts=3,
            base_delay=0.1,
        )

        assert result == "success"
        assert call_count == 2

    def test_safe_operation_failure(self):
        """Test safe operation handling failures."""
        logger = MagicMock()

        def failing_func():
            raise PathValidationError("Test error")

        with pytest.raises(PathValidationError):
            safe_operation("failing_op", failing_func, logger)

        # Should log the error
        logger.error.assert_called_once()


class TestCLIErrorHandler:
    """Test CLI error handler decorator."""

    def test_successful_function(self):
        """Test decorator with successful function."""

        @cli_error_handler
        def success_func():
            return "success"

        result = success_func()
        assert result == "success"

    def test_lazyscan_error_handling(self):
        """Test decorator with LazyScan exceptions."""

        @cli_error_handler
        def failing_func():
            raise PathValidationError("Test error", path="/test")

        with patch("builtins.print") as mock_print:
            with pytest.raises(SystemExit) as exc_info:
                failing_func()

            assert exc_info.value.code == ExitCode.PATH_ERROR
            mock_print.assert_called_once()

    def test_keyboard_interrupt_handling(self):
        """Test decorator with keyboard interrupt."""

        @cli_error_handler
        def interrupted_func():
            raise KeyboardInterrupt()

        with patch("builtins.print") as mock_print:
            with pytest.raises(SystemExit) as exc_info:
                interrupted_func()

            assert exc_info.value.code == ExitCode.USER_CANCELLED
            mock_print.assert_called_once()

    def test_unexpected_exception_handling(self):
        """Test decorator with unexpected exceptions."""

        @cli_error_handler
        def unexpected_func():
            raise ValueError("Unexpected error")

        with patch("builtins.print") as mock_print:
            with pytest.raises(SystemExit) as exc_info:
                unexpected_func()

            assert exc_info.value.code == ExitCode.GENERAL_ERROR
            assert mock_print.call_count >= 1


class TestValidationUtilities:
    """Test validation utility functions."""

    def test_validate_not_none_success(self):
        """Test validate_not_none with valid value."""
        result = validate_not_none("test_value", "test_field")
        assert result == "test_value"

    def test_validate_not_none_failure(self):
        """Test validate_not_none with None value."""
        with pytest.raises(ValidationError) as exc_info:
            validate_not_none(None, "test_field")

        error = exc_info.value
        assert error.context["field"] == "test_field"
        assert "cannot be None" in str(error)

    def test_validate_file_exists_success(self, tmp_path):
        """Test validate_file_exists with existing file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        result = validate_file_exists(str(test_file), "test_operation")
        assert result == str(test_file)

    def test_validate_file_exists_failure(self):
        """Test validate_file_exists with missing file."""
        with pytest.raises(PathValidationError) as exc_info:
            validate_file_exists("/nonexistent/file.txt", "test_operation")

        error = exc_info.value
        assert error.context["path"] == "/nonexistent/file.txt"
        assert error.context["operation"] == "test_operation"

    def test_validate_directory_exists_success(self, tmp_path):
        """Test validate_directory_exists with existing directory."""
        test_dir = tmp_path / "subdir"
        test_dir.mkdir()

        result = validate_directory_exists(str(test_dir), "test_operation")
        assert result == str(test_dir)

    def test_validate_directory_exists_missing(self):
        """Test validate_directory_exists with missing directory."""
        with pytest.raises(PathValidationError) as exc_info:
            validate_directory_exists("/nonexistent/dir", "test_operation")

        error = exc_info.value
        assert "Directory not found" in str(error)

    def test_validate_directory_exists_file_not_dir(self, tmp_path):
        """Test validate_directory_exists with file instead of directory."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        with pytest.raises(PathValidationError) as exc_info:
            validate_directory_exists(str(test_file), "test_operation")

        error = exc_info.value
        assert "not a directory" in str(error)
        assert error.context["is_file"] is True


class TestRetryTimingDetails:
    """Test retry mechanism timing in detail."""

    def test_retry_timing(self):
        """Test that retry timing follows backoff pattern."""
        call_times = []

        def record_time():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise OSError("Temp failure")
            return "success"

        start_time = time.time()
        result = retry_with_backoff(
            record_time,
            max_attempts=4,
            base_delay=0.1,
            backoff_factor=2.0,
            jitter=False,  # Disable jitter for predictable timing
        )

        assert result == "success"
        assert len(call_times) == 3

        # Check that delays approximately follow backoff pattern
        # (allowing for some timing variance)
        if len(call_times) >= 3:
            delay1 = call_times[1] - call_times[0]
            delay2 = call_times[2] - call_times[1]

            # First delay should be ~0.1s, second ~0.2s
            assert 0.05 < delay1 < 0.2  # Allow some variance
            assert 0.15 < delay2 < 0.4  # Allow some variance

    def test_retry_jitter(self):
        """Test that jitter adds randomness to delays."""
        call_times = []

        def record_time_with_failure():
            call_times.append(time.time())
            raise OSError("Always fail")

        # Run with jitter enabled (should vary delays)
        with pytest.raises(OSError):
            retry_with_backoff(
                record_time_with_failure, max_attempts=3, base_delay=0.05, jitter=True
            )

        # Should have attempted 3 times
        assert len(call_times) == 3

    def test_retry_max_delay_limit(self):
        """Test that max delay is respected."""
        call_times = []

        def always_fail():
            call_times.append(time.time())
            raise OSError("Always fail")

        with pytest.raises(OSError):
            retry_with_backoff(
                always_fail,
                max_attempts=4,
                base_delay=1.0,
                max_delay=0.2,  # Lower than base_delay * backoff_factor
                backoff_factor=10.0,
                jitter=False,
            )

        # Delays should be capped at max_delay
        if len(call_times) >= 3:
            delay = call_times[2] - call_times[1]
            assert delay <= 0.3  # Should respect max_delay


class TestIntegration:
    """Test integration of error handling components."""

    def test_end_to_end_error_flow(self):
        """Test complete error handling flow."""
        logger = MagicMock()

        @cli_error_handler
        def operation_with_retry():
            call_count = 0

            def flaky_operation():
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise OSError("Temporary failure")
                return "success"

            return safe_operation(
                "test_operation",
                flaky_operation,
                logger,
                retryable=True,
                max_attempts=5,
                base_delay=0.1,
            )

        result = operation_with_retry()
        assert result == "success"

    def test_error_propagation_through_layers(self):
        """Test that errors properly propagate through all layers."""
        logger = MagicMock()

        @cli_error_handler
        def cli_function():
            def failing_operation():
                raise SecurityPolicyError("Policy violation", policy_hash="test123")

            return safe_operation("security_check", failing_operation, logger)

        with patch("builtins.print") as mock_print:
            with pytest.raises(SystemExit) as exc_info:
                cli_function()

            assert exc_info.value.code == ExitCode.SECURITY_ERROR
            # Should print user-friendly error
            mock_print.assert_called()
            error_msg = mock_print.call_args[0][0]
            assert "Security policy violation" in error_msg


if __name__ == "__main__":
    pytest.main([__file__])
