#!/usr/bin/env python3
"""
Integration tests for error handling with structured logging framework.
"""

import json
import tempfile
import pytest
from unittest.mock import patch

from lazyscan.core.errors import (
    PathValidationError,
    SecurityPolicyError,
    DeletionSafetyError,
    handle_exception,
    safe_operation,
    cli_error_handler
)
from lazyscan.core.logging_config import (
    setup_logging,
    get_logger,
    configure_audit_logging,
    get_audit_logger
)


class TestErrorLoggingIntegration:
    """Test integration between error handling and logging."""
    
    def test_structured_logging_with_error_context(self):
        """Test that error context is properly logged in structured format."""
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as log_file:
            # Setup structured logging
            setup_logging(
                console_format='json',
                log_level='DEBUG',
                log_file=log_file.name
            )
            
            logger = get_logger(__name__)
            
            # Create error with context
            error = PathValidationError(
                "Invalid path detected", 
                path="/invalid/path"
            )
            
            # Handle the error (this should log it)
            result = handle_exception(error, logger, "path_validation", re_raise=False)
            
            # Read the logged data
            log_file.seek(0)
            log_content = log_file.read()
            
            # Parse the JSON log entry
            log_lines = [line.strip() for line in log_content.split('\n') if line.strip()]
            assert len(log_lines) >= 1
            
            log_entry = json.loads(log_lines[-1])  # Get the last (most recent) entry
            
            # Verify structured logging captured error details
            assert log_entry['level'] == 'ERROR'
            assert "path_validation" in log_entry['message']
            assert log_entry['exception_type'] == 'PathValidationError'
            assert log_entry['operation'] == 'path_validation'
            assert log_entry['context']['path'] == '/invalid/path'
    
    def test_safe_operation_logging_integration(self):
        """Test safe operation with logging integration."""
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as log_file:
            setup_logging(
                console_format='json',
                log_level='DEBUG',
                log_file=log_file.name
            )
            
            logger = get_logger(__name__)
            
            def failing_operation():
                raise SecurityPolicyError(
                    "Policy violation detected",
                    policy_hash="abc123"
                )
            
            # This should log the error and re-raise it
            with pytest.raises(SecurityPolicyError):
                safe_operation("security_check", failing_operation, logger)
            
            # Read and verify the log
            log_file.seek(0)
            log_content = log_file.read()
            
            log_lines = [line.strip() for line in log_content.split('\n') if line.strip()]
            
            # Should have both debug (operation start) and error entries
            assert len(log_lines) >= 2
            
            # Find the error log entry
            error_entry = None
            for line in log_lines:
                entry = json.loads(line)
                if entry['level'] == 'ERROR':
                    error_entry = entry
                    break
            
            assert error_entry is not None
            assert error_entry['exception_type'] == 'SecurityPolicyError'
            assert error_entry['operation'] == 'security_check'
            assert error_entry['context']['policy_hash'] == 'abc123'
    
    def test_security_exception_audit_logging(self):
        """Test that security exceptions are logged to audit trail."""
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as main_log, \
             tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as audit_log:
            
            # Setup main logging
            setup_logging(
                console_format='json',
                log_level='INFO',
                log_file=main_log.name
            )
            
            # Setup audit logging
            configure_audit_logging(audit_log.name, audit_level='INFO')
            
            logger = get_logger(__name__)
            
            # Create and handle a security exception
            error = SecurityPolicyError(
                "Critical path access denied",
                policy_hash="def456"
            )
            
            handle_exception(error, logger, "critical_deletion", re_raise=False)
            
            # Check main log
            main_log.seek(0)
            main_content = main_log.read()
            main_lines = [line.strip() for line in main_content.split('\n') if line.strip()]
            
            main_entry = json.loads(main_lines[-1])
            assert main_entry['exception_type'] == 'SecurityPolicyError'
            assert main_entry['operation'] == 'critical_deletion'
            
            # Check audit log
            audit_log.seek(0)
            audit_content = audit_log.read()
            audit_lines = [line.strip() for line in audit_content.split('\n') if line.strip()]
            
            audit_entry = json.loads(audit_lines[-1])
            assert audit_entry['event_type'] == 'exception_occurred'
            assert audit_entry['security_event'] is True
            assert audit_entry['operation'] == 'critical_deletion'
            assert audit_entry['context']['policy_hash'] == 'def456'
    
    def test_deletion_safety_error_audit_logging(self):
        """Test that deletion safety errors are logged to audit trail."""
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as audit_log:
            configure_audit_logging(audit_log.name, audit_level='INFO')
            
            logger = get_logger(__name__)
            
            error = DeletionSafetyError(
                "Attempted to delete critical system path",
                path="/usr/bin",
                reason="critical_system_path"
            )
            
            handle_exception(error, logger, "delete_files", re_raise=False)
            
            # Check audit log
            audit_log.seek(0)
            audit_content = audit_log.read()
            audit_lines = [line.strip() for line in audit_content.split('\n') if line.strip()]
            
            audit_entry = json.loads(audit_lines[-1])
            assert audit_entry['event_type'] == 'exception_occurred'
            assert audit_entry['security_event'] is True
            assert audit_entry['context']['path'] == '/usr/bin'
            assert audit_entry['context']['safety_reason'] == 'critical_system_path'
    
    def test_cli_error_handler_with_structured_logging(self):
        """Test CLI error handler with structured logging."""
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as log_file:
            setup_logging(
                console_format='human',
                log_level='ERROR',
                log_file=log_file.name,
                enable_colors=False  # For predictable output
            )
            
            @cli_error_handler
            def failing_cli_operation():
                raise PathValidationError(
                    "Path validation failed",
                    path="/bad/path"
                )
            
            # Mock the console adapter to capture the error output
            from unittest.mock import Mock
            console_mock = Mock()
            
            # Patch the console adapter where it's imported in the CLI error handler
            with patch('lazyscan.core.logging_config.get_console', return_value=console_mock):
                with pytest.raises(SystemExit) as exc_info:
                    failing_cli_operation()
            
            # Verify console adapter was called with formatted error
            console_mock.print_error.assert_called()
            
            # Get the error message that was passed to console
            error_message = console_mock.print_error.call_args[0][0]
            
            assert "❌" in error_message
            assert "Path validation failed" in error_message
            assert "/bad/path" in error_message
            assert "💡" in error_message  # Should include suggestion
            
            # Verify exit code
            assert exc_info.value.code == 3  # PATH_ERROR exit code
            
            # Check that structured logging also occurred in the file
            log_file.seek(0)
            log_content = log_file.read()
            
            # Should have JSON log entry from the console adapter's internal logging
            log_lines = [line.strip() for line in log_content.split('\n') if line.strip()]
            if log_lines:  # CLI handler logs through console adapter
                log_entry = json.loads(log_lines[-1])
                # Verify it's our error type
                assert log_entry['level'] == 'ERROR'


class TestContextPropagation:
    """Test that error context propagates properly through logging layers."""
    
    def test_nested_operation_context_preservation(self):
        """Test that context is preserved through nested operations."""
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as log_file:
            setup_logging(
                console_format='json',
                log_level='DEBUG',
                log_file=log_file.name
            )
            
            logger = get_logger(__name__)
            
            def outer_operation():
                def inner_operation():
                    raise PathValidationError(
                        "Inner validation failed",
                        path="/nested/path"
                    )
                
                return safe_operation("inner_op", inner_operation, logger)
            
            with pytest.raises(PathValidationError):
                safe_operation("outer_op", outer_operation, logger)
            
            # Read and verify nested context is preserved
            log_file.seek(0)
            log_content = log_file.read()
            
            log_lines = [line.strip() for line in log_content.split('\n') if line.strip()]
            
            # Find error entries
            error_entries = []
            for line in log_lines:
                entry = json.loads(line)
                if entry['level'] == 'ERROR':
                    error_entries.append(entry)
            
            assert len(error_entries) >= 2  # Should have errors from both operations
            
            # Last error should be from outer operation
            outer_error = error_entries[-1]
            assert outer_error['operation'] == 'outer_op'
            assert outer_error['exception_type'] == 'PathValidationError'
            
            # Should preserve original error context
            inner_error = error_entries[0]
            assert inner_error['operation'] == 'inner_op'
            assert inner_error['context']['path'] == '/nested/path'


class TestBackwardsCompatibility:
    """Test that error handling still works with standard Python logging."""
    
    def test_fallback_to_standard_logging(self):
        """Test fallback when structured logging isn't available."""
        import logging
        
        # Use standard Python logger
        standard_logger = logging.getLogger('test_fallback')
        
        error = PathValidationError("Test error", path="/test")
        
        # Should not raise exceptions even without structured logging
        result = handle_exception(error, standard_logger, "test_op", re_raise=False)
        
        assert result['exception_type'] == 'PathValidationError'
        assert result['operation'] == 'test_op'
        assert result['context']['path'] == '/test'


if __name__ == "__main__":
    pytest.main([__file__])
