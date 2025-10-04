#!/usr/bin/env python3
"""
Tests for the retention policy engine.
"""

import os
import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from lazyscan.core.retention_policy import RetentionPolicyEngine, CleanupOperation, CleanupResult
from lazyscan.core.cache_targets import CacheTarget, SafetyLevel


class TestRetentionPolicyEngine:
    """Test the retention policy engine functionality."""

    def test_engine_initialization(self):
        """Test that the engine initializes correctly."""
        config = {
            "allow_admin_operations": True,
            "confirm_deletions": False,
            "safe_delete_enabled": True
        }
        engine = RetentionPolicyEngine(config)

        assert engine.allow_admin_operations is True
        assert engine.confirm_deletions is False
        assert engine.safe_delete_enabled is True

    def test_apply_policies_to_empty_list(self):
        """Test applying policies to an empty list of targets."""
        engine = RetentionPolicyEngine({})
        operations = engine.apply_retention_policies([])

        assert len(operations) == 0

    def test_disabled_target_skipped(self):
        """Test that disabled targets are skipped."""
        engine = RetentionPolicyEngine({})

        # Create a disabled target
        target = CacheTarget(
            path=Path("/tmp/test"),
            category="test",
            enabled=False
        )

        operations = engine.apply_retention_policies([target], dry_run=True)

        assert len(operations) == 1
        assert operations[0].result == CleanupResult.SKIPPED
        assert "disabled" in operations[0].error_message.lower()

    def test_admin_required_target_without_permission(self):
        """Test that admin-required targets are skipped when admin not allowed."""
        engine = RetentionPolicyEngine({"allow_admin_operations": False})

        target = CacheTarget(
            path=Path("/tmp/test"),
            category="test",
            requires_admin=True
        )

        operations = engine.apply_retention_policies([target], dry_run=True)

        assert len(operations) == 1
        assert operations[0].result == CleanupResult.REQUIRES_ADMIN

    def test_admin_required_target_with_permission(self):
        """Test that admin-required targets are processed when admin allowed."""
        engine = RetentionPolicyEngine({"allow_admin_operations": True})

        target = CacheTarget(
            path=Path("/tmp/test"),
            category="test",
            requires_admin=True
        )

        operations = engine.apply_retention_policies([target], dry_run=True)

        assert len(operations) == 1
        # Should be skipped due to no expired files, not admin requirements
        assert operations[0].result == CleanupResult.SKIPPED
        assert "expired files" in operations[0].error_message.lower()

    def test_dangerous_target_requires_confirmation(self):
        """Test that dangerous targets require confirmation."""
        engine = RetentionPolicyEngine({})

        target = CacheTarget(
            path=Path("/tmp/test"),
            category="test",
            safety_level=SafetyLevel.DANGEROUS
        )

        operations = engine.apply_retention_policies([target], dry_run=True, force=False)

        assert len(operations) == 1
        assert operations[0].result == CleanupResult.SKIPPED
        assert "requires confirmation" in operations[0].error_message.lower()

    def test_dangerous_target_with_force(self):
        """Test that dangerous targets are processed when forced."""
        engine = RetentionPolicyEngine({})

        target = CacheTarget(
            path=Path("/tmp/test"),
            category="test",
            safety_level=SafetyLevel.DANGEROUS
        )

        operations = engine.apply_retention_policies([target], dry_run=True, force=True)

        assert len(operations) == 1
        # Should be skipped due to no expired files, not safety level
        assert operations[0].result == CleanupResult.SKIPPED
        assert "expired files" in operations[0].error_message.lower()

    def test_safe_target_processed(self):
        """Test that safe targets are processed normally."""
        engine = RetentionPolicyEngine({})

        target = CacheTarget(
            path=Path("/tmp/test"),
            category="test",
            safety_level=SafetyLevel.SAFE
        )

        operations = engine.apply_retention_policies([target], dry_run=True)

        assert len(operations) == 1
        assert operations[0].result == CleanupResult.SKIPPED  # No expired files
        assert "expired files" in operations[0].error_message.lower()

    def test_cleanup_summary_generation(self):
        """Test that cleanup summaries are generated correctly."""
        engine = RetentionPolicyEngine({})

        # Create mock operations
        operations = [
            CleanupOperation(
                target=CacheTarget(Path("/tmp/test1"), "test", retention_days=30),
                files_to_delete=[Path("/tmp/test1/file1")],
                total_size_mb=10.0,
                result=CleanupResult.SUCCESS
            ),
            CleanupOperation(
                target=CacheTarget(Path("/tmp/test2"), "test", retention_days=30),
                files_to_delete=[],
                total_size_mb=0.0,
                result=CleanupResult.SKIPPED,
                error_message="No expired files"
            ),
            CleanupOperation(
                target=CacheTarget(Path("/tmp/test3"), "test", retention_days=30),
                files_to_delete=[Path("/tmp/test3/file1")],
                total_size_mb=5.0,
                result=CleanupResult.FAILED,
                error_message="Permission denied"
            )
        ]

        summary = engine.get_cleanup_summary(operations)

        assert summary["total_operations"] == 3
        assert summary["successful_operations"] == 1
        assert summary["skipped_operations"] == 1
        assert summary["failed_operations"] == 1
        assert summary["total_files_deleted"] == 2
        assert summary["total_size_mb"] == 15.0
        assert len(summary["operations"]) == 3

    def test_file_age_calculation(self):
        """Test that file age calculation works correctly."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_file = Path(f.name)

        try:
            # Create target with 1 day retention
            target = CacheTarget(
                path=temp_file,
                category="test",
                retention_days=1
            )

            # File should not be expired (just created)
            assert not target.is_expired

            # Modify the file's timestamp to be old
            old_time = time.time() - (2 * 24 * 3600)  # 2 days ago
            os.utime(temp_file, (old_time, old_time))

            # Now it should be expired
            assert target.is_expired

        finally:
            temp_file.unlink(missing_ok=True)

    def test_directory_age_calculation(self):
        """Test that directory age calculation works correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a file in the directory
            test_file = temp_path / "test.txt"
            test_file.write_text("test content")

            # Create target with 1 day retention
            target = CacheTarget(
                path=temp_path,
                category="test",
                retention_days=1
            )

            # Should not be expired initially
            assert not target.is_expired

            # Make the file old
            old_time = time.time() - (2 * 24 * 3600)  # 2 days ago
            os.utime(test_file, (old_time, old_time))

            # Now the directory should be considered expired
            assert target.is_expired