#!/usr/bin/env python3
"""
Tests for formatting utilities.
"""

import unittest
from lazyscan.core.formatting import parse_size, human_readable


class TestFormatting(unittest.TestCase):
    """Test formatting utilities."""

    def test_parse_size_basic(self):
        """Test basic size parsing."""
        self.assertEqual(parse_size("1B"), 1)
        self.assertEqual(parse_size("1KB"), 1024)
        self.assertEqual(parse_size("1MB"), 1024 * 1024)
        self.assertEqual(parse_size("1GB"), 1024 * 1024 * 1024)

    def test_parse_size_case_insensitive(self):
        """Test case insensitive parsing."""
        self.assertEqual(parse_size("1mb"), 1024 * 1024)
        self.assertEqual(parse_size("1Gb"), 1024 * 1024 * 1024)

    def test_parse_size_without_unit(self):
        """Test parsing without explicit unit."""
        self.assertEqual(parse_size("1024"), 1024)

    def test_parse_size_decimal(self):
        """Test decimal size parsing."""
        self.assertEqual(parse_size("1.5MB"), int(1.5 * 1024 * 1024))
        self.assertEqual(parse_size("0.5GB"), int(0.5 * 1024 * 1024 * 1024))

    def test_parse_size_invalid(self):
        """Test invalid size strings."""
        with self.assertRaises(ValueError):
            parse_size("invalid")

        with self.assertRaises(ValueError):
            parse_size("1XB")  # Invalid unit

        with self.assertRaises(ValueError):
            parse_size("")  # Empty string

    def test_human_readable(self):
        """Test human readable size formatting."""
        self.assertEqual(human_readable(0), "0 B")
        self.assertEqual(human_readable(512), "512 B")
        self.assertEqual(human_readable(1024), "1 KB")
        self.assertEqual(human_readable(1536), "1.5 KB")
        self.assertEqual(human_readable(1024 * 1024), "1 MB")
        self.assertEqual(human_readable(1024 * 1024 * 1024), "1 GB")


if __name__ == "__main__":
    unittest.main()