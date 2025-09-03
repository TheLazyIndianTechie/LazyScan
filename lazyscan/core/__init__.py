#!/usr/bin/env python3
"""
Core functionality modules for LazyScan.
Contains fundamental utilities for scanning, formatting, configuration, and UI.
"""

from . import formatting
from . import scanner
from . import config
from . import ui
from . import logging_config

# Import key functions for convenience
from .formatting import human_readable, get_terminal_colors
from .scanner import get_disk_usage, scan_directory_with_progress
from .config import get_config, has_seen_disclaimer
from .ui import show_logo, show_disclaimer
from .logging_config import get_logger, get_console

__all__ = [
    'formatting',
    'scanner', 
    'config',
    'ui',
    'logging_config',
    'human_readable',
    'get_terminal_colors',
    'get_disk_usage',
    'scan_directory_with_progress',
    'get_config',
    'has_seen_disclaimer',
    'show_logo',
    'show_disclaimer',
    'get_logger',
    'get_console'
]
