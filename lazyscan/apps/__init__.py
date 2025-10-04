#!/usr/bin/env python3
"""
LazyScan application-specific modules.
Contains cache management logic for various applications.
"""

# Import application modules
from . import chrome
from . import unity
from . import unreal

# Import key functions
from .unity import (
    handle_unity_discovery,
    handle_unity_projects_integration,
    scan_unity_project_via_hub,
    prompt_unity_project_selection,
)

from .unreal import handle_unreal_discovery

from .chrome import handle_chrome_discovery, CHROME_PATHS

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
