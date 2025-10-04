#!/usr/bin/env python3
"""
Tests for Chrome browser cache discovery and management.
"""

import sys
from unittest.mock import patch, MagicMock, ANY

import pytest

from lazyscan.apps.chrome import handle_chrome_discovery


@pytest.fixture
def mock_chrome_report():
    """Provide a mock Chrome cache report."""
    return {
        "installed": True,
        "total_size": 1000,
        "safe_size": 600,
        "unsafe_size": 400,
        "chrome_base": "/Users/test/Library/Application Support/Google/Chrome",
        "profiles": [
            {"name": "Profile 1", "total_size": 700},
            {"name": "Default", "total_size": 300},
        ],
        "categories": {
            "safe": {
                "Cache": [
                    ("/path/to/cache1", 100, "file"),
                    ("/path/to/cache2", 200, "dir"),
                ],
                "Code Cache": [("/path/to/code_cache", 300, "dir")],
            },
            "unsafe": {
                "Bookmarks": [("/path/to/bookmarks", 100, "file")],
                "History": [("/path/to/history", 300, "file")],
            },
        },
    }


class TestChromeDiscovery:
    """Test Chrome discovery and cleanup."""

    def test_non_macos_platform(self):
        """Test that the function exits on non-macOS platforms."""
        with patch.object(sys, "platform", "linux"):
            with patch("lazyscan.apps.chrome.console") as mock_console:
                handle_chrome_discovery(MagicMock())
                mock_console.print.assert_called_with(
                    "\nError: --chrome option is only available on macOS."
                )

    @patch("lazyscan.apps.chrome.logger")
    @patch("lazyscan.apps.chrome.scan_chrome_cache_helper")
    def test_scan_chrome_cache_helper_exception(
        self, mock_scan_chrome_cache_helper, mock_logger
    ):
        """Test that an exception from scan_chrome_cache_helper is handled."""
        mock_scan_chrome_cache_helper.side_effect = Exception("Test exception")
        with patch.object(sys, "platform", "darwin"):
            with patch("lazyscan.apps.chrome.console"):
                handle_chrome_discovery(MagicMock())
                mock_logger.error(
                    "Chrome cache analysis failed",
                    extra={"error": "Test exception"},
                    exc_info=ANY,
                )

    @patch("lazyscan.apps.chrome.get_terminal_colors")
    @patch("lazyscan.apps.chrome.scan_chrome_cache_helper")
    def test_chrome_not_installed(
        self, mock_scan_chrome_cache_helper, mock_get_terminal_colors
    ):
        """Test the case where Chrome is not installed."""
        mock_get_terminal_colors.return_value = (
            "[CYAN]",
            "[MAGENTA]",
            "[YELLOW]",
            "[RESET]",
            "[BOLD]",
            "[BRIGHT_CYAN]",
            "[BRIGHT_MAGENTA]",
            "[GREEN]",
            "[RED]",
        )
        mock_scan_chrome_cache_helper.return_value = {"installed": False}
        with patch.object(sys, "platform", "darwin"):
            with patch("lazyscan.apps.chrome.console") as mock_console:
                handle_chrome_discovery(MagicMock())
                assert "Chrome is not installed" in mock_console.print.call_args[0][0]

    @patch("builtins.input", return_value="q")
    @patch("lazyscan.apps.chrome.get_terminal_colors")
    @patch("lazyscan.apps.chrome.scan_chrome_cache_helper")
    def test_user_quits(
        self,
        mock_scan_chrome_cache_helper,
        mock_get_terminal_colors,
        mock_input,
        mock_chrome_report,
    ):
        """Test the user quitting the cleanup process."""
        mock_get_terminal_colors.return_value = (
            "[CYAN]",
            "[MAGENTA]",
            "[YELLOW]",
            "[RESET]",
            "[BOLD]",
            "[BRIGHT_CYAN]",
            "[BRIGHT_MAGENTA]",
            "[GREEN]",
            "[RED]",
        )
        mock_scan_chrome_cache_helper.return_value = mock_chrome_report
        with patch.object(sys, "platform", "darwin"):
            with patch("lazyscan.apps.chrome.console") as mock_console:
                handle_chrome_discovery(MagicMock())
                assert "Chrome cleanup cancelled" in mock_console.print.call_args[0][0]

    @patch("os.path.isfile", return_value=True)
    @patch("os.path.isdir", return_value=True)
    @patch("os.remove")
    @patch("shutil.rmtree")
    @patch("builtins.input", side_effect=["a", "y"])
    @patch("lazyscan.apps.chrome.get_terminal_colors")
    @patch("lazyscan.apps.chrome.scan_chrome_cache_helper")
    def test_clean_all_safe_categories(
        self,
        mock_scan_chrome_cache_helper,
        mock_get_terminal_colors,
        mock_input,
        mock_rmtree,
        mock_remove,
        mock_isdir,
        mock_isfile,
        mock_chrome_report,
    ):
        """Test cleaning all safe categories."""
        mock_get_terminal_colors.return_value = (
            "[CYAN]",
            "[MAGENTA]",
            "[YELLOW]",
            "[RESET]",
            "[BOLD]",
            "[BRIGHT_CYAN]",
            "[BRIGHT_MAGENTA]",
            "[GREEN]",
            "[RED]",
        )
        mock_scan_chrome_cache_helper.return_value = mock_chrome_report
        with patch.object(sys, "platform", "darwin"):
            with patch("lazyscan.apps.chrome.console"):
                handle_chrome_discovery(MagicMock())
                assert mock_rmtree.call_count == 2
                assert mock_remove.call_count == 1
