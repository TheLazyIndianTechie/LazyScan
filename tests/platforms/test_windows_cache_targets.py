#!/usr/bin/env python3
"""
Tests for Windows cache target functionality.
"""

import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from lazyscan.platforms.windows import get_windows_cache_targets
from lazyscan.core.cache_targets import SafetyLevel


class TestWindowsCacheTargets:
    """Test Windows cache target discovery and configuration."""

    @patch.dict(os.environ, {
        "TEMP": "/tmp/test_temp",
        "TMP": "/tmp/test_tmp",
        "WINDIR": "/tmp/test_windows",
        "LOCALAPPDATA": "/tmp/test_local"
    })
    def test_default_cache_targets_with_mocked_paths(self):
        """Test that default cache targets are returned when paths exist."""
        # Mock paths to exist
        with patch.object(Path, 'exists', return_value=True):
            targets = get_windows_cache_targets()

            # Should have temp and prefetch by default (thumbnail may not exist in mock)
            temp_targets = [t for t in targets if t.category == "temporary_files"]
            prefetch_targets = [t for t in targets if t.category == "system_performance"]

            assert len(temp_targets) >= 1  # At least one temp directory
            assert len(prefetch_targets) == 1

            # Check temp target properties
            temp = temp_targets[0]
            assert temp.safety_level == SafetyLevel.SAFE
            assert temp.retention_days == 7
            assert not temp.requires_admin

            # Check prefetch target properties
            prefetch = prefetch_targets[0]
            assert prefetch.safety_level == SafetyLevel.SAFE
            assert prefetch.retention_days == 30
            assert prefetch.requires_admin

    @patch.dict(os.environ, {
        "TEMP": "/tmp/test_temp",
        "WINDIR": "/tmp/test_windows",
        "LOCALAPPDATA": "/tmp/test_local"
    })
    def test_configured_cache_targets(self):
        """Test that cache targets respect configuration."""
        config = {
            "windows": {
                "temp": {"enabled": True, "retention_days": 14, "safety_level": "caution"},
                "prefetch": {"enabled": False},  # Disabled
                "windows_update": {"enabled": True},  # Enabled (dangerous)
                "thumbnail": {"enabled": True}
            }
        }

        # Mock paths to exist
        with patch.object(Path, 'exists', return_value=True):
            targets = get_windows_cache_targets(config)

            # Should have temp, windows_update, and thumbnail
            temp_targets = [t for t in targets if t.category == "temporary_files"]
            update_targets = [t for t in targets if t.category == "system_updates"]
            thumbnail_targets = [t for t in targets if t.category == "thumbnails"]
            prefetch_targets = [t for t in targets if t.category == "system_performance"]

            assert len(temp_targets) == 1
            assert len(update_targets) == 1
            assert len(thumbnail_targets) == 1
            assert len(prefetch_targets) == 0  # Disabled

            # Check modified temp retention
            temp = temp_targets[0]
            assert temp.retention_days == 14
            assert temp.safety_level == SafetyLevel.CAUTION

            # Check windows update is dangerous
            update = update_targets[0]
            assert update.safety_level == SafetyLevel.DANGEROUS

    def test_no_targets_when_paths_dont_exist(self):
        """Test that no targets are returned when Windows paths don't exist."""
        # This is the real scenario on non-Windows systems
        targets = get_windows_cache_targets()
        assert len(targets) == 0

    @patch.dict(os.environ, {"TEMP": "/tmp/test_temp"})
    def test_temp_path_handling(self):
        """Test that temp paths are handled correctly."""
        with patch.object(Path, 'exists', return_value=True):
            targets = get_windows_cache_targets()

            temp_targets = [t for t in targets if t.category == "temporary_files"]
            assert len(temp_targets) == 1

            temp = temp_targets[0]
            assert str(temp.path) == "/tmp/test_temp"

    def test_empty_config_returns_defaults(self):
        """Test that empty config returns default targets when paths exist."""
        config = {}

        # Mock minimal environment
        with patch.dict(os.environ, {"TEMP": "/tmp/test_temp", "WINDIR": "/tmp/test_windows"}):
            with patch.object(Path, 'exists', return_value=True):
                targets = get_windows_cache_targets(config)

                # Should return temp and prefetch
                categories = [t.category for t in targets]
                assert "temporary_files" in categories
                assert "system_performance" in categories

    def test_disabled_dangerous_targets_by_default(self):
        """Test that dangerous targets are disabled by default."""
        # Mock environment with all paths existing
        with patch.dict(os.environ, {
            "TEMP": "/tmp/test_temp",
            "WINDIR": "/tmp/test_windows",
            "LOCALAPPDATA": "/tmp/test_local"
        }):
            with patch.object(Path, 'exists', return_value=True):
                targets = get_windows_cache_targets()

                # Should not have dangerous targets by default
                dangerous_targets = [t for t in targets if t.safety_level == SafetyLevel.DANGEROUS]
                assert len(dangerous_targets) == 0