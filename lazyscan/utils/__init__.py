#!/usr/bin/env python3
"""
LazyScan Utilities Module

Provides common utilities and helper functions:
- Structured logging configuration
- Console adapters
- IO utilities
- Formatting helpers
"""

from .logging_config import (
    configure_logging,
    get_logger,
    log_with_context,
    get_console_adapter,
    ConsoleAdapter,
    StructuredFormatter,
    ConsoleFormatter
)

__all__ = [
    'configure_logging',
    'get_logger', 
    'log_with_context',
    'get_console_adapter',
    'ConsoleAdapter',
    'StructuredFormatter',
    'ConsoleFormatter'
]
