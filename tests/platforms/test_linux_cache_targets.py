#!/usr/bin/env python3
"""
Tests for Linux cache target functionality.
"""

import pytest
from pathlib import Path
from lazyscan.platforms.linux import get_linux_cache_targets
from lazyscan.core.cache_targets import SafetyLevel


class TestLinuxCacheTargets:
    """Test Linux cache target discovery and configuration."""

    def test_default_cache_targets(self):
        """Test that default cache targets are returned correctly."""
        targets = get_linux_cache_targets()

        # Should have at least user_cache and tmp by default
        assert len(targets) >= 2

        # Check user cache target
        user_cache = next((t for t in targets if t.category == "user_cache"), None)
        assert user_cache is not None
        assert user_cache.safety_level == SafetyLevel.CAUTION
        assert user_cache.retention_days == 30
        assert not user_cache.requires_admin

        # Check tmp target
        tmp = next((t for t in targets if t.category == "temporary_files"), None)
        assert tmp is not None
        assert tmp.safety_level == SafetyLevel.CAUTION
        assert tmp.retention_days == 7

    def test_configured_cache_targets(self):
        """Test that cache targets respect configuration."""
        config = {
            "linux": {
                "user_cache": {"enabled": True, "retention_days": 60, "safety_level": "safe"},
                "tmp": {"enabled": False},  # Disabled
                "apt": {"enabled": True},  # Would be enabled if path exists
                "docker": {"enabled": True}  # Enabled (dangerous)
            }
        }

        targets = get_linux_cache_targets(config)

        # Should have user_cache, and potentially apt/docker if paths exist
        # tmp should be disabled
        tmp = next((t for t in targets if t.category == "temporary_files"), None)
        assert tmp is None

        # Check modified user cache retention
        user_cache = next((t for t in targets if t.category == "user_cache"), None)
        assert user_cache is not None
        assert user_cache.retention_days == 60
        assert user_cache.safety_level == SafetyLevel.SAFE

    def test_cache_target_paths_exist_or_reasonable(self):
        """Test that cache target paths are reasonable."""
        targets = get_linux_cache_targets()

        for target in targets:
            # Paths should be absolute
            assert target.path.is_absolute()

            # Should be Path objects
            assert isinstance(target.path, Path)

            # Should have reasonable categories
            assert target.category in ["user_cache", "package_manager", "temporary_files", "system_logs", "container"]

    def test_empty_config_returns_defaults(self):
        """Test that empty config returns default targets."""
        targets = get_linux_cache_targets({})

        # Should still return default targets
        assert len(targets) >= 2
        categories = [t.category for t in targets]
        assert "user_cache" in categories
        assert "temporary_files" in categories

    def test_disabled_dangerous_targets_by_default(self):
        """Test that dangerous targets are disabled by default."""
        targets = get_linux_cache_targets()

        # Journal and docker should not be present by default
        dangerous_targets = [t for t in targets if t.safety_level == SafetyLevel.DANGEROUS]
        assert len(dangerous_targets) == 0