#!/usr/bin/env python3
"""
Core functionality modules for LazyScan.
Contains fundamental utilities for scanning, formatting, configuration, and UI.
"""

from . import config, formatting, logging_config, scanner, ui
from .config import get_config, has_seen_disclaimer

# Import key functions for convenience
from .formatting import get_terminal_colors, human_readable
from .logging_config import get_console, get_logger
from .scanner import get_disk_usage, scan_directory_with_progress
from .ui import show_disclaimer, show_logo

__all__ = [
    "formatting",
    "scanner",
    "config",
    "ui",
    "logging_config",
    "human_readable",
    "get_terminal_colors",
    "get_disk_usage",
    "scan_directory_with_progress",
    "get_config",
    "has_seen_disclaimer",
    "show_logo",
    "show_disclaimer",
    "get_logger",
    "get_console",
]
