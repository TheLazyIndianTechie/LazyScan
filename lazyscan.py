#!/usr/bin/env python3
"""
lazyscan: A lazy way to find what's eating your disk space.

Backward compatibility wrapper for the refactored modular LazyScan.
The main functionality has been moved to lazyscan.cli.main for better organization.
"""

# Import the main CLI function for backward compatibility
from lazyscan.cli.main import cli_main, main

__version__ = "0.5.0"
__all__ = ["main", "cli_main"]

if __name__ == "__main__":
    main()
