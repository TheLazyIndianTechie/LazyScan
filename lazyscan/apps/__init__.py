#!/usr/bin/env python3
"""
LazyScan application-specific modules.
Contains cache management logic for various applications.
"""

# Import application modules
from . import chrome, unity, unreal
from .chrome import CHROME_PATHS, handle_chrome_discovery

# Import key functions
from .unity import (
    handle_unity_discovery,
    handle_unity_projects_integration,
    prompt_unity_project_selection,
    scan_unity_project_via_hub,
)
from .unreal import handle_unreal_discovery

__all__ = [
    "chrome",
    "unity",
    "unreal",
    "handle_unity_discovery",
    "handle_unity_projects_integration",
    "scan_unity_project_via_hub",
    "prompt_unity_project_selection",
    "handle_unreal_discovery",
    "handle_chrome_discovery",
    "CHROME_PATHS",
]
