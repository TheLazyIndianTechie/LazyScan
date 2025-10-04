#!/usr/bin/env python3
"""
LazyScan CLI module.
Command-line interface and argument parsing.
"""

from .main import main, cli_main
from .main_argparse import create_argument_parser

__all__ = ["main", "cli_main", "create_argument_parser"]
