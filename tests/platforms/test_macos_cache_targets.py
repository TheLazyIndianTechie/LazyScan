#!/usr/bin/env python3
"""
Tests for macOS cache target functionality.
"""

import pytest
from pathlib import Path
from lazyscan.platforms.macos import get_macos_cache_targets
from lazyscan.core.cache_targets import SafetyLevel


class TestMacOSCacheTargets:
    """Test macOS cache target discovery and configuration."""

    def test_default_cache_targets(self):
        """Test that default cache targets are returned correctly."""
        targets = get_macos_cache_targets()

        # Should have 3 targets by default (Homebrew, npm, pip - Docker disabled)
        assert len(targets) == 3

        # Check Homebrew target
        homebrew = next((t for t in targets if "Homebrew" in str(t.path)), None)
        assert homebrew is not None
        assert homebrew.category == "package_manager"
        assert homebrew.safety_level == SafetyLevel.SAFE
        assert homebrew.retention_days == 30
        assert not homebrew.requires_admin

        # Check npm target
        npm = next((t for t in targets if ".npm" in str(t.path)), None)
        assert npm is not None
        assert npm.category == "package_manager"
        assert npm.safety_level == SafetyLevel.SAFE
        assert npm.retention_days == 90

        # Check pip target
        pip = next((t for t in targets if "pip" in str(t.path)), None)
        assert pip is not None
        assert pip.category == "package_manager"
        assert pip.safety_level == SafetyLevel.SAFE
        assert pip.retention_days == 90

    def test_configured_cache_targets(self):
        """Test that cache targets respect configuration."""
        config = {
            "macos": {
                "homebrew": {"enabled": True, "retention_days": 60, "safety_level": "safe"},
                "npm": {"enabled": False},  # Disabled
                "pip": {"enabled": True, "retention_days": 120},
                "docker": {"enabled": True}  # Enabled (dangerous)
            }
        }

        targets = get_macos_cache_targets(config)

        # Should have Homebrew, pip, and docker (npm disabled)
        assert len(targets) == 3

        # Check modified Homebrew retention
        homebrew = next((t for t in targets if "Homebrew" in str(t.path)), None)
        assert homebrew is not None
        assert homebrew.retention_days == 60

        # npm should be missing
        npm = next((t for t in targets if ".npm" in str(t.path)), None)
        assert npm is None

        # Check modified pip retention
        pip = next((t for t in targets if "pip" in str(t.path)), None)
        assert pip is not None
        assert pip.retention_days == 120

        # Check docker is enabled and dangerous
        docker = next((t for t in targets if "docker" in str(t.path)), None)
        assert docker is not None
        assert docker.safety_level == SafetyLevel.DANGEROUS

    def test_cache_target_paths_exist_or_reasonable(self):
        """Test that cache target paths are reasonable (may not exist in test env)."""
        targets = get_macos_cache_targets()

        for target in targets:
            # Paths should be absolute
            assert target.path.is_absolute()

            # Should be Path objects
            assert isinstance(target.path, Path)

            # Should have reasonable categories
            assert target.category in ["package_manager", "container"]

    def test_empty_config_returns_defaults(self):
        """Test that empty config returns default targets."""
        targets = get_macos_cache_targets({})

        # Should still return the 3 default targets
        assert len(targets) == 3
        categories = [t.category for t in targets]
        assert all(cat == "package_manager" for cat in categories)