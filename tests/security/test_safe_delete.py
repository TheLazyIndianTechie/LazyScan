#!/usr/bin/env python3
"""
Tests for SafeDeleter module.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from lazyscan.core.errors import DeletionSafetyError
from lazyscan.security.safe_delete import (
    DeletionMode,
    SafeDeleter,
    get_safe_deleter,
    safe_delete,
)


class TestSafeDeleter:
    def setup_method(self):
        """Setup for each test method."""
        self.deleter = SafeDeleter()

    def test_kill_switch_blocks_deletion(self):
        """Test that global kill switch blocks all deletions."""
        with patch.dict(os.environ, {"LAZYSCAN_DISABLE_DELETIONS": "1"}):
            deleter = SafeDeleter()
            test_path = Path("/tmp/test")

            with pytest.raises(DeletionSafetyError) as exc_info:
                deleter.delete(test_path, dry_run=False)

            assert "kill switch" in str(exc_info.value).lower()

    def test_dry_run_mode(self):
        """Test that dry run mode doesn't actually delete."""
        test_path = Path("/tmp/nonexistent")

        # Should return True for dry run without actually doing anything
        result = self.deleter.delete(test_path, dry_run=True)
        assert result is True

    def test_critical_path_rejection(self):
        """Test that critical system paths are rejected."""
        critical_paths = [
            Path.home(),
            Path("/"),
            Path("C:\\") if os.name == "nt" else Path("/usr"),
        ]

        for critical_path in critical_paths:
            if critical_path.exists():
                with pytest.raises(DeletionSafetyError) as exc_info:
                    self.deleter.delete(critical_path, dry_run=False)

                assert "critical system path" in str(exc_info.value).lower()

    def test_symlink_rejection(self, tmp_path):
        """Test that symlinks are rejected."""
        # Create a test file and symlink to it
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("test content")

        test_symlink = tmp_path / "test_symlink"
        test_symlink.symlink_to(test_file)

        with pytest.raises(DeletionSafetyError) as exc_info:
            self.deleter.delete(test_symlink, dry_run=False)

        assert "symlink" in str(exc_info.value).lower()

    def test_context_parameter_passed(self, tmp_path):
        """Test that context parameter is properly used."""
        deleter = SafeDeleter()

        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        # Should succeed in dry run regardless of context
        result = deleter.delete(test_file, context="unity", dry_run=True)
        assert result is True

    def test_send2trash_failure_handling(self, tmp_path):
        """Test handling of send2trash failures."""
        deleter = SafeDeleter()

        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        with patch("lazyscan.security.safe_delete.send2trash") as mock_send2trash:
            mock_send2trash.send2trash.side_effect = Exception("Trash failed")

            with pytest.raises(DeletionSafetyError, match="Trash deletion failed"):
                deleter.delete(test_file, mode=DeletionMode.TRASH, dry_run=False)

    def test_permanent_deletion_interactive_confirmation(self, tmp_path):
        """Test permanent deletion interactive confirmation."""
        deleter = SafeDeleter()

        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        # Mock TTY and user input
        with patch("sys.stdin.isatty", return_value=True):
            with patch("builtins.input", return_value="CANCEL"):
                with patch("builtins.print"):
                    result = deleter.delete(
                        test_file, mode=DeletionMode.PERMANENT, dry_run=False
                    )
                    assert result is False


class TestGlobalFunctions:
    """Test global convenience functions."""

    def test_get_safe_deleter_singleton(self):
        """Test that get_safe_deleter returns singleton instance."""
        deleter1 = get_safe_deleter()
        deleter2 = get_safe_deleter()

        assert deleter1 is deleter2
        assert isinstance(deleter1, SafeDeleter)

    def test_safe_delete_convenience_function(self, tmp_path):
        """Test safe_delete convenience function."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        # Should work in dry run mode
        result = safe_delete(test_file, dry_run=True)
        assert result is True
        assert test_file.exists()


class TestDeletionModes:
    """Test DeletionMode enumeration."""

    def test_mode_values(self):
        """Test that deletion modes have correct values."""
        assert DeletionMode.TRASH.value == "trash"
        assert DeletionMode.PERMANENT.value == "permanent"

    def test_mode_comparison(self):
        """Test that modes can be compared."""
        assert DeletionMode.TRASH != DeletionMode.PERMANENT
        assert DeletionMode.TRASH == DeletionMode.TRASH


if __name__ == "__main__":
    pytest.main([__file__])
