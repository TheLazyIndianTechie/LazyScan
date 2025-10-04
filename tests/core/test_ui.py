#!/usr/bin/env python3
"""
Tests for UI components including themes and responsive layouts.
"""

import unittest
from unittest.mock import patch, MagicMock
from io import StringIO
import shutil

from lazyscan.core.ui import (
    Theme,
    ThemeManager,
    get_theme,
    get_terminal_size,
    show_logo,
    show_disclaimer,
    display_scan_results_header,
    display_scan_summary,
    display_cache_cleanup_summary,
    knight_rider_animation,
)


class TestThemeManager(unittest.TestCase):
    """Test theme loading and management functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset global theme cache
        import lazyscan.core.ui as ui_module
        ui_module._current_theme = None

    def test_default_theme_structure(self):
        """Test that default theme has all required fields."""
        theme = ThemeManager.DEFAULT_THEME

        self.assertIsInstance(theme, Theme)
        self.assertIsInstance(theme.primary, str)
        self.assertIsInstance(theme.accent, str)
        self.assertIsInstance(theme.warning, str)
        self.assertIsInstance(theme.success, str)
        self.assertIsInstance(theme.logo, list)
        self.assertIsInstance(theme.glyphs, dict)
        self.assertIsInstance(theme.animations, dict)

    def test_load_default_theme(self):
        """Test loading the default theme."""
        with patch('lazyscan.core.ui.get_config') as mock_config:
            mock_config.return_value = {}

            theme = ThemeManager.load_theme("default")

            self.assertEqual(theme.primary, ThemeManager.DEFAULT_THEME.primary)
            self.assertEqual(theme.accent, ThemeManager.DEFAULT_THEME.accent)
            self.assertEqual(theme.logo, ThemeManager.DEFAULT_THEME.logo)

    def test_load_custom_theme(self):
        """Test loading a custom theme from config."""
        custom_theme_data = {
            "primary": "\033[31m",  # Red
            "accent": "\033[32m",   # Green
            "logo": ["Custom Logo Line 1", "Custom Logo Line 2"]
        }

        with patch('lazyscan.core.ui.get_config') as mock_config:
            mock_config.return_value = {"themes": {"custom": custom_theme_data}}

            theme = ThemeManager.load_theme("custom")

            self.assertEqual(theme.primary, "\033[31m")
            self.assertEqual(theme.accent, "\033[32m")
            self.assertEqual(theme.logo, ["Custom Logo Line 1", "Custom Logo Line 2"])
            # Should fallback to defaults for missing fields
            self.assertEqual(theme.warning, ThemeManager.DEFAULT_THEME.warning)

    def test_unicode_art_toggle(self):
        """Test Unicode art toggle functionality."""
        with patch('lazyscan.core.ui.get_config') as mock_config:
            # Test with Unicode art enabled
            mock_config.return_value = {"ui": {"unicode_art": True}}
            theme_unicode = ThemeManager.load_theme("default")

            self.assertIn("🐍", theme_unicode.glyphs["file_python"])

            # Test with Unicode art disabled
            mock_config.return_value = {"ui": {"unicode_art": False}}
            theme_ascii = ThemeManager.load_theme("default")

            self.assertEqual(theme_ascii.glyphs["file_python"], "[PY]")
            self.assertEqual(theme_ascii.logo[0], "+----------------------------------------------+")

    def test_theme_validation(self):
        """Test theme configuration validation."""
        # Valid config
        valid_config = {
            "themes": {
                "test_theme": {
                    "primary": "\033[36m",
                    "accent": "\033[35m",
                    "warning": "\033[33m",
                    "success": "\033[92m",
                    "logo": ["Line 1", "Line 2"],
                    "glyphs": {
                        "scanner": "▮▯▯",
                        "progress_filled": "█",
                    },
                    "animations": {
                        "knight_rider_delay": 0.1,
                        "progress_update_interval": 0.2,
                    }
                }
            }
        }

        errors = ThemeManager.validate_theme_config(valid_config)
        self.assertEqual(len(errors), 0)

        # Invalid config - missing required field
        invalid_config = {
            "themes": {
                "bad_theme": {
                    "primary": "\033[36m",
                    # Missing accent, warning, success, logo
                }
            }
        }

        errors = ThemeManager.validate_theme_config(invalid_config)
        self.assertGreater(len(errors), 0)
        self.assertIn("missing required key", " ".join(errors))

    def test_ui_config_validation(self):
        """Test UI configuration validation."""
        # Valid UI config
        valid_config = {
            "ui": {
                "unicode_art": True,
                "theme": "cyberpunk"
            },
            "themes": {
                "cyberpunk": {
                    "primary": "\033[36m",
                    "accent": "\033[35m",
                    "warning": "\033[33m",
                    "success": "\033[92m",
                    "logo": ["Logo"],
                    "glyphs": {"scanner": "▮▯▯"},
                    "animations": {"knight_rider_delay": 0.07}
                }
            }
        }

        errors = ThemeManager.validate_config(valid_config)
        self.assertEqual(len(errors), 0)

        # Invalid UI config - non-existent theme
        invalid_config = {
            "ui": {
                "theme": "nonexistent"
            },
            "themes": {
                "existing_theme": {}
            }
        }

        errors = ThemeManager.validate_config(invalid_config)
        self.assertGreater(len(errors), 0)


class TestResponsiveLayout(unittest.TestCase):
    """Test responsive layout functionality."""

    def test_get_terminal_size(self):
        """Test terminal size detection with fallback."""
        # Test normal case
        with patch('shutil.get_terminal_size') as mock_size:
            mock_size.return_value = type('MockSize', (), {'columns': 100, 'lines': 25})()
            cols, lines = get_terminal_size()
            self.assertEqual(cols, 100)
            self.assertEqual(lines, 25)

        # Test fallback on error
        with patch('shutil.get_terminal_size', side_effect=OSError):
            cols, lines = get_terminal_size()
            self.assertEqual(cols, 120)  # Default fallback
            self.assertEqual(lines, 30)   # Default fallback


class TestUISnapshots(unittest.TestCase):
    """Snapshot tests for UI output."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset global theme cache
        import lazyscan.core.ui as ui_module
        ui_module._current_theme = None

    def _capture_console_output(self, func, *args, **kwargs):
        """Capture console output from a UI function."""
        with patch('lazyscan.core.ui.console') as mock_console:
            func(*args, **kwargs)

            # Collect all print calls
            output_lines = []
            for call in mock_console.print.call_args_list:
                output_lines.append(call[0][0])  # First argument is the message

            return "\n".join(output_lines)

    def test_show_logo_default_theme(self):
        """Test logo display with default theme."""
        with patch('lazyscan.core.ui.get_config') as mock_config, \
             patch('lazyscan.core.ui.console') as mock_console:
            mock_config.return_value = {"ui": {"unicode_art": True}}

            show_logo()

            # Should have made print calls for each logo line
            self.assertTrue(len(mock_console.print.call_args_list) > 0)
            # Check that at least one call contains "LAZY SCAN"
            logo_text = " ".join(str(call[0][0]) if call[0] else "" for call in mock_console.print.call_args_list)
            self.assertIn("LAZY SCAN", logo_text)
            self.assertIn("The Lazy Developer's Disk Tool", logo_text)

    def test_show_logo_ascii_fallback(self):
        """Test logo display with ASCII fallback."""
        with patch('lazyscan.core.ui.get_config') as mock_config, \
             patch('lazyscan.core.ui.console') as mock_console:
            mock_config.return_value = {"ui": {"unicode_art": False}}

            show_logo()

            # Should have made print calls
            self.assertTrue(len(mock_console.print.call_args_list) > 0)
            # Check for ASCII box drawing
            logo_text = " ".join(str(call[0][0]) if call[0] else "" for call in mock_console.print.call_args_list)
            self.assertIn("+", logo_text)
            self.assertIn("-", logo_text)

    def test_show_disclaimer_with_unicode(self):
        """Test disclaimer display with Unicode art enabled."""
        with patch('lazyscan.core.ui.get_config') as mock_config, \
             patch('lazyscan.core.ui.console') as mock_console:
            mock_config.return_value = {"ui": {"unicode_art": True}}

            show_disclaimer()

            # Should have made print calls
            self.assertTrue(len(mock_console.print.call_args_list) > 0)
            # Check for Unicode warning emoji
            disclaimer_text = " ".join(str(call[0][0]) if call[0] else "" for call in mock_console.print.call_args_list)
            self.assertIn("⚠️", disclaimer_text)
            self.assertIn("LAZYSCAN DISCLAIMER", disclaimer_text)

    def test_show_disclaimer_ascii_fallback(self):
        """Test disclaimer display with ASCII fallback."""
        with patch('lazyscan.core.ui.get_config') as mock_config, \
             patch('lazyscan.core.ui.console') as mock_console:
            mock_config.return_value = {"ui": {"unicode_art": False}}

            show_disclaimer()

            # Should have made print calls
            self.assertTrue(len(mock_console.print.call_args_list) > 0)
            # Check for ASCII WARNING text
            disclaimer_text = " ".join(str(call[0][0]) if call[0] else "" for call in mock_console.print.call_args_list)
            self.assertIn("WARNING", disclaimer_text)
            self.assertNotIn("⚠️", disclaimer_text)

    def test_display_scan_results_header(self):
        """Test scan results header display."""
        with patch('lazyscan.core.ui.console') as mock_console:
            display_scan_results_header(5)

            # Should have made print calls
            self.assertTrue(len(mock_console.print.call_args_list) > 0)
            # Check for expected text
            header_text = " ".join(str(call[0][0]) if call[0] else "" for call in mock_console.print.call_args_list)
            self.assertIn("TARGET ACQUIRED", header_text)
            self.assertIn("5 SPACE HOGS IDENTIFIED", header_text)

    def test_display_scan_summary(self):
        """Test scan summary display."""
        with patch('lazyscan.core.ui.console') as mock_console:
            display_scan_summary(1024 * 1024, "/test/path")

            # Should have made print calls
            self.assertTrue(len(mock_console.print.call_args_list) > 0)
            # Check for expected text
            summary_text = " ".join(str(call[0][0]) if call[0] else "" for call in mock_console.print.call_args_list)
            self.assertIn("Total data volume", summary_text)
            self.assertIn("1 MB", summary_text)
            self.assertIn("Target directory", summary_text)
            self.assertIn("/test/path", summary_text)

    def test_display_cache_cleanup_summary(self):
        """Test cache cleanup summary display."""
        with patch('lazyscan.core.ui.console') as mock_console:
            display_cache_cleanup_summary(
                512 * 1024,  # freed_bytes
                1024 * 1024,  # used_before
                512 * 1024,   # used_after
                2048 * 1024,  # total_before
                1536 * 1024,  # total_after
                1024 * 1024,  # free_before
                1536 * 1024   # free_after
            )

            # Should have made print calls
            self.assertTrue(len(mock_console.print.call_args_list) > 0)
            # Check for expected text
            summary_text = " ".join(str(call[0][0]) if call[0] else "" for call in mock_console.print.call_args_list)
            self.assertIn("CACHE CLEANUP SUMMARY", summary_text)
            self.assertIn("Space Freed", summary_text)
            self.assertIn("512 KB", summary_text)

    @patch('sys.stdout')
    @patch('time.sleep')  # Mock sleep to speed up test
    def test_knight_rider_animation_interactive(self, mock_sleep, mock_stdout):
        """Test Knight Rider animation in interactive mode."""
        with patch('sys.stdout.isatty', return_value=True), \
             patch('lazyscan.core.ui.get_config') as mock_config:

            mock_config.return_value = {"ui": {"use_colors": True}}

            # Capture stdout writes
            written_data = []
            mock_stdout.write = lambda data: written_data.append(data)
            mock_stdout.flush = MagicMock()

            knight_rider_animation("Scanning", iterations=1)

            # Should have written animation frames
            output = "".join(written_data)
            self.assertIn("Scanning", output)
            self.assertIn("\r", output)  # Carriage returns for animation

    @patch('sys.stdout')
    def test_knight_rider_animation_non_interactive(self, mock_stdout):
        """Test Knight Rider animation in non-interactive mode."""
        with patch('sys.stdout.isatty', return_value=False), \
             patch('lazyscan.core.ui.get_config') as mock_config, \
             patch('lazyscan.core.ui.console') as mock_console:

            mock_config.return_value = {"ui": {"use_colors": True}}

            knight_rider_animation("Scanning", iterations=1)

            # Should have made print calls
            self.assertTrue(len(mock_console.print.call_args_list) > 0)
            # Check for expected text
            animation_text = " ".join(str(call[0][0]) if call[0] else "" for call in mock_console.print.call_args_list)
            self.assertIn("Scanning...", animation_text)
            self.assertNotIn("\r", animation_text)  # No carriage returns


class TestResponsiveBehavior(unittest.TestCase):
    """Test responsive behavior with different terminal sizes."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset global theme cache
        import lazyscan.core.ui as ui_module
        ui_module._current_theme = None

    @patch('shutil.get_terminal_size')
    def test_small_terminal_size(self, mock_size):
        """Test UI behavior with small terminal."""
        # Mock small terminal
        mock_size.return_value = type('MockSize', (), {'columns': 50, 'lines': 20})()

        cols, lines = get_terminal_size()
        self.assertEqual(cols, 50)
        self.assertEqual(lines, 20)

    @patch('shutil.get_terminal_size')
    def test_large_terminal_size(self, mock_size):
        """Test UI behavior with large terminal."""
        # Mock large terminal
        mock_size.return_value = type('MockSize', (), {'columns': 200, 'lines': 50})()

        cols, lines = get_terminal_size()
        self.assertEqual(cols, 200)
        self.assertEqual(lines, 50)

    @patch('shutil.get_terminal_size')
    def test_terminal_size_error_fallback(self, mock_size):
        """Test fallback when terminal size detection fails."""
        mock_size.side_effect = OSError("No terminal")

        cols, lines = get_terminal_size()
        self.assertEqual(cols, 120)  # Default fallback
        self.assertEqual(lines, 30)   # Default fallback


if __name__ == '__main__':
    unittest.main()