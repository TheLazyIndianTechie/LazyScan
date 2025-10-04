#!/usr/bin/env python3
"""
Tests for path validation module.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch

from lazyscan.security.validators import (
    canonicalize_path,
    is_within_allowed_roots,
    is_symlink_or_reparse,
    is_critical_system_path,
    validate_user_supplied_path,
    validate_unity_path,
    validate_unreal_path,
    validate_chrome_path,
    expand_unreal_engine_paths,
)
from lazyscan.core.errors import PathValidationError


class TestCanonicalizePathx:
    """Test path canonicalization with validation."""

    def test_basic_canonicalization(self):
        """Test basic path canonicalization."""
        path = canonicalize_path("~/test")
        assert path.is_absolute()
        assert str(path).startswith(str(Path.home()))

    def test_empty_path_rejected(self):
        """Test that empty paths are rejected."""
        with pytest.raises(PathValidationError, match="cannot be empty"):
            canonicalize_path("")

    def test_none_path_rejected(self):
        """Test that None paths are rejected."""
        with pytest.raises(PathValidationError, match="cannot be empty"):
            canonicalize_path(None)

    def test_control_characters_rejected(self):
        """Test that paths with control characters are rejected."""
        with pytest.raises(PathValidationError, match="control characters"):
            canonicalize_path("/tmp/test\x00file")

    def test_mixed_separators_rejected(self):
        """Test that paths with mixed separators are rejected."""
        with pytest.raises(PathValidationError, match="mixed separators"):
            canonicalize_path("/tmp\\test/file")

    def test_whitespace_rejected(self):
        """Test that paths with leading/trailing whitespace are rejected."""
        with pytest.raises(PathValidationError, match="whitespace"):
            canonicalize_path(" /tmp/test ")

    @pytest.mark.skipif(os.name != "nt", reason="Windows-specific test")
    def test_windows_reserved_names_rejected(self):
        """Test that Windows reserved device names are rejected."""
        for name in ["CON", "PRN", "AUX", "NUL"]:
            with pytest.raises(PathValidationError, match="reserved name"):
                canonicalize_path(f"C:\\temp\\{name}.txt")

    @pytest.mark.skipif(os.name != "nt", reason="Windows-specific test")
    def test_windows_trailing_dots_rejected(self):
        """Test that Windows paths with trailing dots are rejected."""
        with pytest.raises(PathValidationError, match="ends with dot"):
            canonicalize_path("C:\\temp\\file.")


class TestIsWithinAllowedRoots:
    """Test allowed roots validation."""

    def test_path_within_roots(self, tmp_path):
        """Test that path within allowed roots passes."""
        test_dir = tmp_path / "subdir"
        test_dir.mkdir()

        allowed_roots = [tmp_path]
        assert is_within_allowed_roots(test_dir, allowed_roots) is True

    def test_path_outside_roots(self, tmp_path):
        """Test that path outside allowed roots fails."""
        other_dir = Path("/tmp")  # Different from tmp_path
        allowed_roots = [tmp_path]

        assert is_within_allowed_roots(other_dir, allowed_roots) is False

    def test_multiple_roots(self, tmp_path):
        """Test with multiple allowed roots."""
        root1 = tmp_path / "root1"
        root2 = tmp_path / "root2"
        root1.mkdir()
        root2.mkdir()

        test_path = root2 / "subdir"
        test_path.mkdir()

        allowed_roots = [root1, root2]
        assert is_within_allowed_roots(test_path, allowed_roots) is True


class TestIsSymlinkOrReparse:
    """Test symlink detection."""

    def test_regular_file_not_symlink(self, tmp_path):
        """Test that regular files are not detected as symlinks."""
        test_file = tmp_path / "regular.txt"
        test_file.write_text("content")

        assert is_symlink_or_reparse(test_file) is False

    def test_symlink_detected(self, tmp_path):
        """Test that symlinks are detected."""
        target = tmp_path / "target.txt"
        target.write_text("content")

        symlink = tmp_path / "link.txt"
        symlink.symlink_to(target)

        assert is_symlink_or_reparse(symlink) is True


class TestIsCriticalSystemPath:
    """Test critical system path detection."""

    def test_home_directory_is_critical(self):
        """Test that user home directory is considered critical."""
        home = Path.home()
        assert is_critical_system_path(home) is True

    def test_root_directory_is_critical(self):
        """Test that root directory is considered critical."""
        root = Path("/")
        assert is_critical_system_path(root) is True

    def test_system_directories_critical(self):
        """Test that system directories are critical."""
        system_dirs = ["/usr", "/var", "/etc"]
        for dir_path in system_dirs:
            path = Path(dir_path)
            if path.exists():  # Only test if directory exists
                assert is_critical_system_path(path) is True

    def test_temp_directory_not_critical(self):
        """Test that temp directories are not critical."""
        temp_dir = Path("/tmp")
        if temp_dir.exists():
            assert is_critical_system_path(temp_dir) is False


class TestValidateUserSuppliedPath:
    """Test comprehensive path validation."""

    def test_valid_temp_path_general_context(self, tmp_path):
        """Test valid path in general context."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        result = validate_user_supplied_path(test_dir, "general")
        assert isinstance(result, Path)
        assert result.is_absolute()

    def test_critical_path_rejected(self):
        """Test that critical system paths are rejected."""
        with pytest.raises(PathValidationError, match="Critical system path"):
            validate_user_supplied_path(Path.home(), "general")

    def test_symlink_rejected(self, tmp_path):
        """Test that symlinks are rejected."""
        target = tmp_path / "target.txt"
        target.write_text("content")

        symlink = tmp_path / "link.txt"
        symlink.symlink_to(target)

        with pytest.raises(PathValidationError, match="Symlinks"):
            validate_user_supplied_path(symlink, "general")

    def test_context_specific_validation(self, tmp_path):
        """Test context-specific validation with allowed roots."""
        # This should fail because tmp_path is not in Unity allowed roots
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        with pytest.raises(PathValidationError, match="not within allowed roots"):
            validate_user_supplied_path(test_dir, "unity")


class TestUnrealEnginePathExpansion:
    """Test Unreal Engine path discovery."""

    def test_priority_paths_checked_first(self):
        """Test that non-default Unreal paths are checked first."""

        def mock_exists(self):
            # Mock the priority path as existing
            path_str = str(self)
            # Note: Need to normalize since Path objects don't preserve trailing slashes
            target_path = str(Path("/Volumes/LazyGameDevs/Applications/Unreal/UE_5.5/"))
            result = path_str == target_path
            return result

        with patch.object(Path, "exists", mock_exists):
            paths = expand_unreal_engine_paths()

            # Should include the priority path
            priority_path = Path("/Volumes/LazyGameDevs/Applications/Unreal/UE_5.5/")
            assert priority_path in paths
            # Verify it's first in the list (priority)
            assert len(paths) > 0
            assert paths[0] == priority_path

    def test_environment_variable_override(self):
        """Test that LAZYSCAN_UNREAL_PATHS environment variable works."""
        test_path = "/custom/unreal/path"

        with patch.dict(os.environ, {"LAZYSCAN_UNREAL_PATHS": test_path}):
            with patch("pathlib.Path.exists", return_value=True):
                paths = expand_unreal_engine_paths()
                assert Path(test_path) in paths


class TestConvenienceFunctions:
    """Test convenience validation functions."""

    def test_validate_unity_path_calls_correct_context(self):
        """Test that validate_unity_path uses unity context."""
        with patch(
            "lazyscan.security.validators.validate_user_supplied_path"
        ) as mock_validate:
            mock_validate.return_value = Path("/test")

            validate_unity_path("/test/path")

            mock_validate.assert_called_once_with("/test/path", "unity")

    def test_validate_unreal_path_calls_correct_context(self):
        """Test that validate_unreal_path uses unreal context."""
        with patch(
            "lazyscan.security.validators.validate_user_supplied_path"
        ) as mock_validate:
            mock_validate.return_value = Path("/test")

            validate_unreal_path("/test/path")

            mock_validate.assert_called_once_with("/test/path", "unreal")

    def test_validate_chrome_path_calls_correct_context(self):
        """Test that validate_chrome_path uses chrome context."""
        with patch(
            "lazyscan.security.validators.validate_user_supplied_path"
        ) as mock_validate:
            mock_validate.return_value = Path("/test")

            validate_chrome_path("/test/path")

            mock_validate.assert_called_once_with("/test/path", "chrome")


if __name__ == "__main__":
    pytest.main([__file__])
