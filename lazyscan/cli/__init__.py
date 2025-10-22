#!/usr/bin/env python3
"""
LazyScan CLI module.
Command-line interface and argument parsing.
"""

from .main import cli_main, create_argument_parser, main

__all__ = ["main", "cli_main", "create_argument_parser"]
