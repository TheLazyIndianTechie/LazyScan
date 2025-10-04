#!/usr/bin/env python3
"""
Tests for Chromium-based browser cache helpers.
"""

import platform
from unittest.mock import patch, MagicMock
from pathlib import Path

import pytest

from helpers.chromium_cache_helpers import (
    scan_chromium_cache,
    discover_chromium_profiles,
    get_chromium_cache_targets,
    BROWSERS
)


class TestChromiumCacheHelpers:
    """Test Chromium cache helper functions."""

    @pytest.mark.parametrize("browser_name", ["chrome", "edge", "brave"])
    def test_scan_chromium_cache_not_installed(self, browser_name):
        """Test scanning when browser is not installed."""
        with patch.object(Path, "exists", return_value=False):
            result = scan_chromium_cache(browser_name)

            assert result["installed"] is False
            assert result["total_size"] == 0
            assert result["browser_name"] == browser_name

    @pytest.mark.parametrize("browser_name", ["chrome", "edge", "brave"])
    def test_scan_chromium_cache_installed(self, browser_name):
        """Test scanning when browser is installed."""
        with patch.object(Path, "exists", return_value=True), \
             patch("helpers.chromium_cache_helpers.discover_chromium_profiles") as mock_discover, \
             patch("helpers.chromium_cache_helpers.compute_directory_size", return_value=100):

            mock_profile = MagicMock()
            mock_profile.name = "Default"
            mock_profile.caches = [Path("/fake/cache")]
            mock_discover.return_value = [mock_profile]

            result = scan_chromium_cache(browser_name)

            assert result["installed"] is True
            assert result["total_size"] == 100
            assert result["browser_name"] == browser_name

    def test_discover_chromium_profiles_no_data_dir(self):
        """Test profile discovery when data directory doesn't exist."""
        browser = BROWSERS["chrome"]

        with patch.object(Path, "exists", return_value=False):
            profiles = list(discover_chromium_profiles(browser))
            assert profiles == []

    def test_discover_chromium_profiles_with_profiles(self):
        """Test profile discovery with existing profiles."""
        browser = BROWSERS["chrome"]

        with patch.object(Path, "exists", return_value=True), \
             patch.object(Path, "iterdir") as mock_iterdir, \
             patch("helpers.chromium_cache_helpers._is_valid_chromium_profile", return_value=True):

            # Mock profile directory
            mock_profile_dir = MagicMock()
            mock_profile_dir.is_dir.return_value = True
            mock_profile_dir.name = "Default"
            mock_iterdir.return_value = [mock_profile_dir]

            profiles = list(discover_chromium_profiles(browser))

            assert len(profiles) == 1
            assert profiles[0].name == "Default"

    def test_get_chromium_cache_targets(self):
        """Test getting cache targets for browsers."""
        with patch("helpers.chromium_cache_helpers.discover_chromium_profiles") as mock_discover:
            mock_profile = MagicMock()
            mock_profile.name = "Default"
            mock_profile.caches = [Path("/fake/cache")]
            mock_discover.return_value = [mock_profile]

            targets = get_chromium_cache_targets("chrome")

            assert "Default:cache" in targets or "cache" in targets

    def test_get_chromium_cache_targets_specific_profile(self):
        """Test getting cache targets for specific profile."""
        with patch.object(Path, "exists", return_value=True), \
             patch("helpers.chromium_cache_helpers._get_chromium_cache_dirs") as mock_get_caches:

            mock_get_caches.return_value = [Path("/fake/cache")]
            targets = get_chromium_cache_targets("chrome", "/fake/profile")

            assert "cache" in targets

    def test_unknown_browser(self):
        """Test handling of unknown browser."""
        result = scan_chromium_cache("unknown")
        assert result["installed"] is False

        targets = get_chromium_cache_targets("unknown")
        assert targets == {}


class TestBrowserConfigurations:
    """Test browser configuration objects."""

    def test_browser_configurations(self):
        """Test that browser configurations are properly defined."""
        assert "chrome" in BROWSERS
        assert "edge" in BROWSERS
        assert "brave" in BROWSERS

        for name, browser in BROWSERS.items():
            assert browser.name == name
            assert browser.data_dir
            assert browser.display_name

    @pytest.mark.skipif(platform.system() != "Darwin", reason="macOS specific test")
    def test_browser_paths_macos(self):
        """Test browser paths on macOS."""
        for browser in BROWSERS.values():
            path = browser.get_data_path()
            assert "~/Library/Application Support" in str(path) or "Microsoft" in str(path) or "BraveSoftware" in str(path)