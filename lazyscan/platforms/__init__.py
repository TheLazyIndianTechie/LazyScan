#!/usr/bin/env python3
"""
LazyScan platform-specific modules.
Contains platform abstractions for cross-platform compatibility.
"""

from . import macos

# Future: from . import windows, linux

__all__ = ["macos"]
