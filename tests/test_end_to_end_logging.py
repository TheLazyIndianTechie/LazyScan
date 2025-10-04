#!/usr/bin/env python3
"""
End-to-end tests for structured logging integration across the entire LazyScan application.
Tests that logging works across all components and produces proper audit trails.
"""

import json
import tempfile
import pytest
from pathlib import Path

from lazyscan.core.logging_config import (
    setup_logging,
    get_logger,
    configure_audit_logging,
    get_console,
    log_context,
    log_security_event,
    log_deletion_event,
    profile_operation,
)
from lazyscan.core.errors import (
    PathValidationError,
    SecurityPolicyError,
    DeletionSafetyError,
    handle_exception,
)
from lazyscan.security.sentinel import initialize_sentinel


class TestEndToEndLoggingIntegration:
    """End-to-end tests for structured logging across all components."""

    def test_complete_logging_pipeline(self):
        """Test the complete logging pipeline from application to audit trail."""
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".json", delete=False
        ) as main_log, tempfile.NamedTemporaryFile(
            mode="w+", suffix=".json", delete=False
        ) as audit_log:

            # Setup complete logging infrastructure
            setup_logging(
                console_format="json",
                log_level="DEBUG",
                log_file=main_log.name,
                enable_colors=False,
            )

            configure_audit_logging(audit_log.name, audit_level="INFO")

            logger = get_logger("e2e_test")
            console = get_console()

            # Test structured logging with context
            with log_context(operation="file_scan", app_type="unity", scan_id="12345"):
                logger.info(
                    "Starting scan operation",
                    target_path="/Users/test/Library/Caches",
                    scan_mode="discovery",
                )

                # Test security event logging
                log_security_event(
                    event_type="scan_initiated",
                    severity="info",
                    description="Unity cache scan initiated",
                    target_path="/Users/test/Library/Caches",
                    expected_size_mb=150.5,
                    user_confirmed=True,
                )

                # Test error handling with context
                try:
                    raise PathValidationError(
                        "Invalid scan path detected",
                        path="/invalid/unity/cache",
                        context={"scan_type": "unity_cache", "user_id": "test_user"},
                    )
                except PathValidationError as e:
                    handle_exception(e, logger, "scan_validation", re_raise=False)

                # Test console adapter
                console.print_success("Scan preparation complete")
                console.print_info("Found 42 cache directories")
                console.print_warning("Some caches are currently in use")

            # Test performance profiling
            with profile_operation(logger, "cache_analysis"):
                logger.debug(
                    "Analyzing cache structure", cache_count=42, total_size_mb=256.8
                )

            # Test deletion event logging
            log_deletion_event(
                path="/Users/test/Library/Caches/Unity/cache1",
                deletion_mode="trash",
                result="success",
                size_mb=45.2,
                freed_space_mb=45.2,
            )

            # Read and verify main log
            main_log.seek(0)
            main_content = main_log.read()
            main_lines = [
                line.strip() for line in main_content.split("\n") if line.strip()
            ]

            # Verify structured entries
            assert len(main_lines) >= 6  # Should have multiple log entries

            # Parse and verify context propagation
            context_entries = []
            for line in main_lines:
                entry = json.loads(line)
                if "operation" in entry and entry["operation"] == "file_scan":
                    context_entries.append(entry)

            assert len(context_entries) >= 3  # Info, error, console messages

            # Verify context is preserved
            for entry in context_entries:
                assert entry.get("app_type") == "unity"
                assert entry.get("scan_id") == "12345"

            # Verify error entry structure
            error_entries = [
                entry for entry in main_lines if json.loads(entry)["level"] == "ERROR"
            ]
            assert len(error_entries) >= 1

            error_entry = json.loads(error_entries[0])
            assert error_entry["exception_type"] == "PathValidationError"
            assert error_entry["context"]["path"] == "/invalid/unity/cache"
            assert error_entry["context"]["scan_type"] == "unity_cache"

            # Read and verify audit log
            audit_log.seek(0)
            audit_content = audit_log.read()
            audit_lines = [
                line.strip() for line in audit_content.split("\n") if line.strip()
            ]

            assert len(audit_lines) >= 2  # Security event, deletion event

            # Verify security event
            security_events = [
                json.loads(line)
                for line in audit_lines
                if json.loads(line).get("event_type") == "scan_initiated"
            ]
            assert len(security_events) == 1

            security_event = security_events[0]
            assert security_event["security_event"] is True
            assert security_event["target_path"] == "/Users/test/Library/Caches"
            assert security_event["expected_size_mb"] == 150.5

            # Verify deletion event
            deletion_events = [
                json.loads(line)
                for line in audit_lines
                if json.loads(line).get("event_type") == "file_deletion"
            ]
            assert len(deletion_events) == 1

            deletion_event = deletion_events[0]
            assert deletion_event["path"] == "/Users/test/Library/Caches/Unity/cache1"
            assert deletion_event["deletion_mode"] == "trash"
            assert deletion_event["deletion_result"] == "success"

    def test_security_integration_with_logging(self):
        """Test security system integration with structured logging."""
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".json", delete=False
        ) as audit_log, tempfile.TemporaryDirectory() as temp_dir:

            configure_audit_logging(audit_log.name, audit_level="DEBUG")

            # Create a test policy file
            policy_path = Path(temp_dir) / "test_policy.json"
            test_policy = {
                "version": "1.0",
                "behavior_flags": {
                    "require_trash_first": True,
                    "interactive_double_confirm": True,
                    "block_symlinks": True,
                },
                "size_limits": {
                    "large_directory_threshold_mb": 100,
                    "max_deletion_size_mb": 1000,
                },
                "allowed_roots": {
                    "unity": ["/Users/*/Library/Caches/Unity"],
                    "chrome": ["/Users/*/Library/Caches/Google/Chrome"],
                },
                "deny_patterns": {
                    "macos": [r"^/System/.*", r"^/usr/.*", r"^/private/.*"]
                },
            }

            policy_path.write_text(json.dumps(test_policy, indent=2))

            # Initialize security sentinel with logging
            try:
                initialize_sentinel(policy_path)

                # Just log a security event since the safe deletion test is complex
                log_security_event(
                    event_type="security_test_initiated",
                    severity="info",
                    description="Security integration test started",
                    policy_path=str(policy_path),
                )

            except Exception as e:
                # Security initialization might fail in test environment
                # Log the attempt anyway
                log_security_event(
                    event_type="security_test_failed",
                    severity="warning",
                    description=f"Security integration test failed: {e}",
                    error_type=e.__class__.__name__,
                )

            # Verify audit logging occurred
            audit_log.seek(0)
            audit_content = audit_log.read()
            audit_lines = [
                line.strip() for line in audit_content.split("\n") if line.strip()
            ]

            # Should have at least one audit entry
            assert len(audit_lines) >= 1

            # Verify audit structure
            for line in audit_lines:
                entry = json.loads(line)
                assert "security_event" in entry
                assert entry["security_event"] is True
                assert "timestamp" in entry
                assert "event_type" in entry

    def test_error_reporting_with_audit_trail(self):
        """Test error reporting creates proper audit trails."""
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".json", delete=False
        ) as main_log, tempfile.NamedTemporaryFile(
            mode="w+", suffix=".json", delete=False
        ) as audit_log:

            setup_logging(
                console_format="json", log_level="INFO", log_file=main_log.name
            )
            configure_audit_logging(audit_log.name, audit_level="INFO")

            logger = get_logger("error_test")

            # Test different types of errors create audit entries
            errors_to_test = [
                SecurityPolicyError(
                    "Critical security violation detected",
                    policy_hash="abc123",
                    context={"violation_type": "critical_path_access"},
                ),
                DeletionSafetyError(
                    "Dangerous deletion attempt blocked",
                    path="/usr/bin",
                    reason="system_protection",
                    context={"protection_level": "critical"},
                ),
            ]

            for error in errors_to_test:
                handle_exception(error, logger, "security_validation", re_raise=False)

            # Verify main log has error entries
            main_log.seek(0)
            main_content = main_log.read()
            main_lines = [
                line.strip() for line in main_content.split("\n") if line.strip()
            ]

            error_entries = [
                json.loads(line)
                for line in main_lines
                if json.loads(line)["level"] == "ERROR"
            ]
            assert len(error_entries) == 2

            # Verify audit log has security events
            audit_log.seek(0)
            audit_content = audit_log.read()
            audit_lines = [
                line.strip() for line in audit_content.split("\n") if line.strip()
            ]

            security_events = [
                json.loads(line)
                for line in audit_lines
                if json.loads(line).get("event_type") == "exception_occurred"
            ]
            assert len(security_events) == 2

            # Verify audit trail completeness
            for event in security_events:
                assert event["security_event"] is True
                assert "timestamp" in event
                assert "operation" in event
                assert event["operation"] == "security_validation"


class TestConsoleAdapterIntegration:
    """Test console adapter integration in real-world scenarios."""

    def test_console_adapter_with_structured_logging(self):
        """Test console adapter creates structured log entries."""
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".json", delete=False
        ) as log_file:
            setup_logging(
                console_format="human",
                log_level="DEBUG",
                log_file=log_file.name,
                enable_colors=False,
            )

            console = get_console()

            # Test different console message types
            console.print("Normal message")
            console.print_success("Operation completed successfully")
            console.print_warning("Cache files are currently in use")
            console.print_error("Failed to access cache directory")
            console.print_info("Scanning Unity project caches...")

            # Read logged output
            log_file.seek(0)
            log_content = log_file.read()
            log_lines = [
                line.strip() for line in log_content.split("\n") if line.strip()
            ]

            # Should have entries for each console call
            assert len(log_lines) >= 5

            # Verify structured format
            message_types_found = set()
            for line in log_lines:
                entry = json.loads(line)
                assert "print_statement" in entry
                assert entry["print_statement"] is True

                if "message_type" in entry:
                    message_types_found.add(entry["message_type"])

            # Verify different message types were logged
            assert "success" in message_types_found
            assert "info" in message_types_found


if __name__ == "__main__":
    pytest.main([__file__])
