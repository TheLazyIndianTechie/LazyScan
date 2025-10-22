#!/usr/bin/env python3
"""
LazyScan - The Lazy Developer's Disk Space Analysis Tool

A comprehensive disk space scanner and cache cleaner with support for:
- Unity and Unreal Engine project cache management
- Chrome, Safari, and other browser cache cleaning
- macOS system cache cleanup
- Secure deletion with audit trails and recovery
- Structured logging and security frameworks
"""

__version__ = "0.5.0"
__author__ = "TheLazyIndianTechie"

# Import main CLI entry point for backward compatibility
from .apps import chrome, unity, unreal
from .cli.main import cli_main, main

# Import key modules for programmatic use
from .core import config, formatting, scanner, ui

__all__ = [
    "main",
    "cli_main",
    "__version__",
    "__author__",
    "formatting",
    "scanner",
    "config",
    "ui",
    "unity",
    "unreal",
    "chrome",
]
