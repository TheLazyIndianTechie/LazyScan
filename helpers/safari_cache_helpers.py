#!/usr/bin/env python3
"""
Safari cache discovery and management helpers for LazyScan.

Provides utilities for Safari cache directory identification on macOS,
with proper permission checks and privilege-aware operations.
"""

import os
import sys
import platform
from pathlib import Path
from typing import List, Dict, Any, Iterator, NamedTuple

from lazyscan.core.logging_config import get_logger

logger = get_logger(__name__)


class SafariCacheInfo(NamedTuple):
    """Represents Safari cache directory information."""
    path: Path
    category: str
    requires_root: bool
    description: str


def compute_directory_size(path: str) -> int:
    """Recursively calculates the total file size of a directory."""
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.exists(fp):
                    try:
                        total_size += os.path.getsize(fp)
                    except (OSError, PermissionError):
                        continue
    except (OSError, PermissionError):
        pass
    return total_size


def scan_safari_cache() -> Dict[str, Any]:
    """
    Scan Safari cache directories on macOS.

    Returns:
        Dictionary containing cache analysis results
    """
    result = {
        "installed": False,
        "total_size": 0,
        "safe_size": 0,
        "unsafe_size": 0,
        "categories": {
            "safe": {},
            "unsafe": {}
        },
        "requires_root": False,
        "platform_supported": platform.system() == "Darwin"
    }

    # Only works on macOS
    if not result["platform_supported"]:
        logger.debug("Safari cache scanning only supported on macOS")
        return result

    try:
        # Get Safari cache directories
        cache_dirs = list(_get_safari_cache_dirs())

        if not cache_dirs:
            logger.debug("No Safari cache directories found")
            return result

        result["installed"] = True

        # Categorize cache items
        safe_items = []
        unsafe_items = []

        for cache_info in cache_dirs:
            if cache_info.path.exists():
                size = compute_directory_size(str(cache_info.path))
                result["total_size"] += size

                if cache_info.requires_root:
                    result["requires_root"] = True
                    result["unsafe_size"] += size
                    unsafe_items.append((str(cache_info.path), size, "dir"))
                else:
                    result["safe_size"] += size
                    safe_items.append((str(cache_info.path), size, "dir"))

        # Organize by category
        if safe_items:
            result["categories"]["safe"]["Safari Cache"] = safe_items
        if unsafe_items:
            result["categories"]["unsafe"]["Safari System Cache"] = unsafe_items

    except Exception as e:
        logger.error(f"Safari cache scan failed: {e}")
        result["error"] = str(e)

    return result


def _get_safari_cache_dirs() -> Iterator[SafariCacheInfo]:
    """Get Safari cache directories with permission requirements."""
    home = Path.home()

    # Safari cache directories - some require root privileges
    safari_caches = [
        # User-accessible caches (safe to delete)
        SafariCacheInfo(
            path=home / "Library/Caches/com.apple.Safari",
            category="Web Cache",
            requires_root=False,
            description="Safari web page cache and temporary files"
        ),
        SafariCacheInfo(
            path=home / "Library/Caches/com.apple.Safari/WebKitCache",
            category="WebKit Cache",
            requires_root=False,
            description="WebKit rendering cache"
        ),
        # System-level caches (require root)
        SafariCacheInfo(
            path=Path("/System/Library/Caches/com.apple.Safari"),
            category="System Safari Cache",
            requires_root=True,
            description="System-wide Safari cache (requires root)"
        ),
        SafariCacheInfo(
            path=Path("/Library/Caches/com.apple.Safari"),
            category="Library Safari Cache",
            requires_root=True,
            description="Library Safari cache (requires root)"
        ),
    ]

    for cache_info in safari_caches:
        # Only yield if directory exists
        if cache_info.path.exists():
            yield cache_info


def check_safari_permissions() -> Dict[str, Any]:
    """
    Check permissions for Safari cache directories.

    Returns:
        Dictionary with permission status for each cache directory
    """
    result = {
        "can_access_user_cache": False,
        "can_access_system_cache": False,
        "is_root": os.geteuid() == 0 if hasattr(os, 'geteuid') else False,
        "permissions": {}
    }

    cache_dirs = list(_get_safari_cache_dirs())

    for cache_info in cache_dirs:
        path_str = str(cache_info.path)
        can_access = False
        error_msg = None

        try:
            # Check if we can list the directory
            if cache_info.path.exists():
                list(cache_info.path.iterdir())
                can_access = True
            else:
                error_msg = "Directory does not exist"
        except (OSError, PermissionError) as e:
            error_msg = str(e)

        result["permissions"][path_str] = {
            "accessible": can_access,
            "requires_root": cache_info.requires_root,
            "error": error_msg
        }

        # Update summary flags
        if cache_info.requires_root:
            if can_access:
                result["can_access_system_cache"] = True
        else:
            if can_access:
                result["can_access_user_cache"] = True

    return result


def get_safari_cache_targets() -> Dict[str, str]:
    """
    Returns a dictionary of cache target directories for Safari.

    Returns:
        Dictionary mapping cache category names to their paths.
    """
    cache_targets = {}

    for cache_info in _get_safari_cache_dirs():
        if cache_info.path.exists():
            cache_targets[cache_info.category] = str(cache_info.path)

    return cache_targets