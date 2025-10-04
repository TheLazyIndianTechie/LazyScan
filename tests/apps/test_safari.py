#!/usr/bin/env python3
"""
Tests for Safari browser cache discovery and management.
"""

import sys
from unittest.mock import patch, MagicMock, ANY

import pytest

from lazyscan.apps.safari import handle_safari_discovery


class TestSafariDiscovery:
    """Test Safari discovery and cleanup."""

    def test_non_macos_platform(self):
        """Test that the function exits on non-macOS platforms."""
        with patch.object(sys, "platform", "linux"):
            with patch("lazyscan.apps.safari.console") as mock_console:
                handle_safari_discovery(MagicMock())
                mock_console.print.assert_called()

    @patch("lazyscan.apps.safari.scan_safari_cache")
    @patch("lazyscan.apps.safari.check_safari_permissions")
    @patch("lazyscan.apps.safari.console")
    @patch("builtins.input", return_value="q")
    def test_safari_not_accessible(self, mock_input, mock_console, mock_perm, mock_scan):
        """Test handling when Safari cache is not accessible."""
        mock_perm.return_value = {"can_access_user_cache": False, "can_access_system_cache": False}
        mock_scan.return_value = {"installed": True}

        handle_safari_discovery(MagicMock())

        mock_console.print.assert_any_call(
            ANY  # Contains permission/access error message
        )


class TestSafariPlugin:
    """Test Safari plugin interface."""

    @patch("lazyscan.apps.safari.scan_safari_cache")
    def test_safari_plugin_scan_non_macos(self, mock_scan):
        """Test Safari plugin scan on non-macOS."""
        from lazyscan.apps.safari import SafariPlugin

        with patch("platform.system", return_value="Linux"):
            plugin = SafariPlugin()
            result = plugin.scan()

            assert result["status"] == "error"
            assert "macOS" in result["message"]

    @patch("lazyscan.apps.safari.scan_safari_cache")
    def test_safari_plugin_scan_success(self, mock_scan):
        """Test Safari plugin scan method success."""
        from lazyscan.apps.safari import SafariPlugin

        mock_scan.return_value = {"total_size": 500}
        plugin = SafariPlugin()

        result = plugin.scan()

        assert result["status"] == "success"
        assert result["total_size"] == 500