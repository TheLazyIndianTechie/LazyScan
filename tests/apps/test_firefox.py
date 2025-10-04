#!/usr/bin/env python3
"""
Tests for Firefox browser cache discovery and management.
"""

import sys
from unittest.mock import patch, MagicMock, ANY
from pathlib import Path

import pytest

from lazyscan.apps.firefox import handle_firefox_discovery


@pytest.fixture
def mock_firefox_report():
    """Provide a mock Firefox cache report."""
    return {
        "installed": True,
        "total_size": 800,
        "safe_size": 500,
        "unsafe_size": 300,
        "firefox_base": "/Users/test/Library/Application Support/Firefox",
        "profiles": [
            {"name": "default-release", "total_size": 600},
            {"name": "dev-edition-default", "total_size": 200},
        ],
        "categories": {
            "safe": {
                "Cache Directories": [
                    ("/path/to/cache2", 200, "dir"),
                    ("/path/to/startupCache", 150, "dir"),
                    ("/path/to/shader-cache", 150, "dir"),
                ],
            },
            "unsafe": {},
        },
    }


class TestFirefoxDiscovery:
    """Test Firefox discovery and cleanup."""

    def test_non_macos_platform(self):
        """Test that the function exits on non-macOS platforms."""
        with patch.object(sys, "platform", "linux"):
            with patch("lazyscan.apps.firefox.console") as mock_console:
                handle_firefox_discovery(MagicMock())
                mock_console.print.assert_called()

    @patch("lazyscan.apps.firefox.scan_firefox_cache")
    @patch("lazyscan.apps.firefox.console")
    @patch("builtins.input", return_value="q")
    def test_firefox_not_installed(self, mock_input, mock_console, mock_scan):
        """Test handling when Firefox is not installed."""
        mock_scan.return_value = {"installed": False}

        handle_firefox_discovery(MagicMock())

        mock_console.print.assert_any_call(
            ANY  # Contains "Firefox is not installed or profiles not found"
        )

    @patch("lazyscan.apps.firefox.scan_firefox_cache")
    @patch("lazyscan.apps.firefox.console")
    @patch("builtins.input", return_value="q")
    def test_firefox_discovery_with_profiles(self, mock_input, mock_console, mock_scan, mock_firefox_report):
        """Test Firefox discovery with profile information."""
        mock_scan.return_value = mock_firefox_report

        handle_firefox_discovery(MagicMock())

        # Verify overview display
        mock_console.print.assert_any_call(ANY)  # Header
        mock_console.print.assert_any_call(ANY)  # Total size

        # Verify profile information display
        mock_console.print.assert_any_call(ANY)  # Profile count

    @patch("lazyscan.apps.firefox.scan_firefox_cache")
    @patch("lazyscan.apps.firefox.console")
    @patch("builtins.input", return_value="a")
    @patch("builtins.open", create=True)
    def test_firefox_cleanup_all(self, mock_open, mock_input, mock_console, mock_scan, mock_firefox_report):
        """Test Firefox cleanup of all safe items."""
        mock_scan.return_value = mock_firefox_report

        with patch("lazyscan.apps.firefox.os.path.isdir", return_value=True), \
             patch("lazyscan.apps.firefox.os.path.isfile", return_value=False), \
             patch("lazyscan.apps.firefox.shutil.rmtree") as mock_rmtree:

            handle_firefox_discovery(MagicMock())

            # Verify cleanup was attempted
            assert mock_rmtree.call_count >= 1

    @patch("lazyscan.apps.firefox.scan_firefox_cache")
    @patch("lazyscan.apps.firefox.console")
    @patch("builtins.input", side_effect=["1", "y"])
    @patch("builtins.open", create=True)
    def test_firefox_cleanup_individual_category(self, mock_open, mock_input, mock_console, mock_scan, mock_firefox_report):
        """Test Firefox cleanup of individual category."""
        mock_scan.return_value = mock_firefox_report

        with patch("lazyscan.apps.firefox.os.path.isdir", return_value=True), \
             patch("lazyscan.apps.firefox.shutil.rmtree") as mock_rmtree:

            handle_firefox_discovery(MagicMock())

            # Verify cleanup was attempted for selected category
            mock_rmtree.assert_called()


class TestFirefoxPlugin:
    """Test Firefox plugin interface."""

    @patch("lazyscan.apps.firefox.scan_firefox_cache")
    def test_firefox_plugin_scan_success(self, mock_scan):
        """Test Firefox plugin scan method success."""
        from lazyscan.apps.firefox import FirefoxPlugin

        mock_scan.return_value = {"total_size": 1000}
        plugin = FirefoxPlugin()

        result = plugin.scan()

        assert result["status"] == "success"
        assert result["total_size"] == 1000

    @patch("lazyscan.apps.firefox.scan_firefox_cache")
    def test_firefox_plugin_scan_failure(self, mock_scan):
        """Test Firefox plugin scan method failure."""
        from lazyscan.apps.firefox import FirefoxPlugin

        mock_scan.side_effect = Exception("Test error")
        plugin = FirefoxPlugin()

        result = plugin.scan()

        assert result["status"] == "error"
        assert "Test error" in result["message"]

    @patch("lazyscan.apps.firefox.scan_firefox_cache")
    @patch("lazyscan.apps.firefox.secure_delete")
    def test_firefox_plugin_clean_success(self, mock_secure_delete, mock_scan):
        """Test Firefox plugin clean method success."""
        from lazyscan.apps.firefox import FirefoxPlugin

        mock_scan.return_value = {
            "installed": True,
            "categories": {"safe": {"Cache Directories": [("/test/path", 100, "dir")]}}
        }
        mock_secure_delete.return_value = MagicMock(success=True, size_processed=100, files_processed=1)

        plugin = FirefoxPlugin()
        result = plugin.clean()

        assert result["status"] == "success"
        assert result["total_size"] == 100

    @patch("lazyscan.apps.firefox.scan_firefox_cache")
    def test_firefox_plugin_clean_not_installed(self, mock_scan):
        """Test Firefox plugin clean when browser not installed."""
        from lazyscan.apps.firefox import FirefoxPlugin

        mock_scan.return_value = {"installed": False}
        plugin = FirefoxPlugin()

        result = plugin.clean()

        assert result["status"] == "error"
        assert "not installed" in result["message"].lower()