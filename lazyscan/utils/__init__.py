#!/usr/bin/env python3
"""
LazyScan Utilities Module

Provides common utilities and helper functions:
- Structured logging configuration
- Console adapters
- IO utilities
- Formatting helpers
"""

from ..core.logging_config import (
    configure_logging,
    get_logger,
    get_console,
    ConsoleAdapter,
    JSONFormatter,
    HumanFormatter,
)

__all__ = [
    "configure_logging",
    "get_logger",
    "get_console",
    "ConsoleAdapter",
    "JSONFormatter",
    "HumanFormatter",
]
