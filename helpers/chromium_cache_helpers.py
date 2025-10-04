#!/usr/bin/env python3
"""
Chromium-based browser cache discovery and management helpers for LazyScan.

Provides utilities for Chrome, Edge, and Brave browser profile enumeration,
cache directory identification, and safe cache cleanup operations.
"""

import os
import platform
from pathlib import Path
from typing import List, Dict, Any, Iterator, NamedTuple

from lazyscan.core.logging_config import get_logger

logger = get_logger(__name__)


class BrowserProfile(NamedTuple):
    """Represents a browser profile with its cache directories."""
    name: str
    path: Path
    caches: List[Path]


class ChromiumBrowser:
    """Configuration for different Chromium-based browsers."""

    def __init__(self, name: str, data_dir: str, display_name: str):
        self.name = name
        self.data_dir = data_dir
        self.display_name = display_name

    def get_data_path(self) -> Path:
        """Get the browser's data directory path."""
        if platform.system() == "Windows":
            # Windows: Use LOCALAPPDATA or APPDATA
            base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~/AppData/Local"))
            return Path(base) / self.data_dir
        else:
            # macOS/Linux: Use Application Support
            base = os.path.expanduser("~/Library/Application Support") if platform.system() == "Darwin" else os.path.expanduser("~/.config")
            return Path(base) / self.data_dir


# Browser configurations
BROWSERS = {
    "chrome": ChromiumBrowser("chrome", "Google/Chrome", "Google Chrome"),
    "edge": ChromiumBrowser("edge", "Microsoft/Edge", "Microsoft Edge"),
    "brave": ChromiumBrowser("brave", "BraveSoftware/Brave-Browser", "Brave Browser"),
}


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


def scan_chromium_cache(browser_name: str) -> Dict[str, Any]:
    """
    Scan cache for a specific Chromium-based browser.

    Args:
        browser_name: Name of the browser ('chrome', 'edge', or 'brave')

    Returns:
        Dictionary containing cache analysis results
    """
    result = {
        "installed": False,
        "total_size": 0,
        "safe_size": 0,
        "unsafe_size": 0,
        "profiles": [],
        "categories": {
            "safe": {},
            "unsafe": {}
        },
        "browser_name": browser_name
    }

    if browser_name not in BROWSERS:
        logger.error(f"Unknown browser: {browser_name}")
        return result

    browser = BROWSERS[browser_name]

    try:
        data_dir = browser.get_data_path()
        result["data_dir"] = str(data_dir)

        # Check if browser is installed
        if not data_dir.exists():
            logger.debug(f"{browser.display_name} data directory not found: {data_dir}")
            return result

        result["installed"] = True

        # Discover profiles
        profiles = list(discover_chromium_profiles(browser))

        if profiles:
            result["profiles"] = []
            for profile in profiles:
                profile_info = {
                    "name": profile.name,
                    "path": str(profile.path),
                    "total_size": 0,
                    "cache_count": len(profile.caches)
                }

                # Calculate profile size
                for cache_dir in profile.caches:
                    if cache_dir.exists():
                        profile_info["total_size"] += compute_directory_size(str(cache_dir))

                result["profiles"].append(profile_info)

        # Categorize cache items
        safe_items = []

        for profile in profiles:
            for cache_dir in profile.caches:
                if cache_dir.exists():
                    size = compute_directory_size(str(cache_dir))
                    result["total_size"] += size
                    result["safe_size"] += size

                    # Add to safe items (Chromium caches are generally safe to delete)
                    safe_items.append((str(cache_dir), size, "dir"))

        # Organize by category
        if safe_items:
            result["categories"]["safe"]["Cache Directories"] = safe_items

    except Exception as e:
        logger.error(f"{browser.display_name} cache scan failed: {e}")
        result["error"] = str(e)

    return result


def discover_chromium_profiles(browser: ChromiumBrowser) -> Iterator[BrowserProfile]:
    """
    Discover profiles for a Chromium-based browser.

    Args:
        browser: ChromiumBrowser configuration

    Yields:
        BrowserProfile instances for each discovered profile
    """
    data_dir = browser.get_data_path()

    if not data_dir.exists():
        return

    # Look for profile directories
    user_data_dir = data_dir / "User Data"
    if user_data_dir.exists():
        # Standard Chromium profile structure
        for item in user_data_dir.iterdir():
            if item.is_dir() and item.name.startswith("Profile ") or item.name == "Default":
                caches = _get_chromium_cache_dirs(item)
                if caches:  # Only yield if there are cache directories
                    yield BrowserProfile(
                        name=item.name,
                        path=item,
                        caches=caches
                    )
    else:
        # Fallback: check if data_dir itself is a profile
        caches = _get_chromium_cache_dirs(data_dir)
        if caches:
            yield BrowserProfile(
                name="Default",
                path=data_dir,
                caches=caches
            )


def _get_chromium_cache_dirs(profile_dir: Path) -> List[Path]:
    """Get SAFE_TO_DELETE cache directories for a Chromium profile."""
    cache_dirs = []

    # Chromium cache directories that are safe to delete
    safe_cache_dirs = [
        "Cache",
        "Code Cache",
        "GPUCache",
        "Service Worker/CacheStorage",
        "Service Worker/ScriptCache",
        "Media Cache",
        "File System",
        "IndexedDB",
        "Local Storage",
        "Session Storage",
        "Web Storage"
    ]

    for cache_name in safe_cache_dirs:
        if "/" in cache_name:
            # Handle subdirectories
            cache_path = profile_dir / cache_name
        else:
            cache_path = profile_dir / cache_name

        if cache_path.exists():
            cache_dirs.append(cache_path)

    return cache_dirs


def get_chromium_cache_targets(browser_name: str, profile_path: str | None = None) -> Dict[str, str]:
    """
    Returns a dictionary of cache target directories for a Chromium browser.

    Args:
        browser_name: Name of the browser ('chrome', 'edge', or 'brave')
        profile_path: Path to a specific profile. If None, discovers all profiles.

    Returns:
        Dictionary mapping cache category names to their paths.
    """
    cache_targets = {}

    if browser_name not in BROWSERS:
        return cache_targets

    browser = BROWSERS[browser_name]

    if profile_path:
        # Specific profile provided
        profile_dir = Path(profile_path)
        if profile_dir.exists():
            caches = _get_chromium_cache_dirs(profile_dir)
            for cache_dir in caches:
                cache_targets[cache_dir.name] = str(cache_dir)
    else:
        # Discover all profiles
        for profile in discover_chromium_profiles(browser):
            for cache_dir in profile.caches:
                cache_targets[f"{profile.name}:{cache_dir.name}"] = str(cache_dir)

    return cache_targets


# Backward compatibility functions
def scan_chrome_cache() -> Dict[str, Any]:
    """Backward compatibility function for Chrome scanning."""
    return scan_chromium_cache("chrome")


def scan_edge_cache() -> Dict[str, Any]:
    """Scan Microsoft Edge cache."""
    return scan_chromium_cache("edge")


def scan_brave_cache() -> Dict[str, Any]:
    """Scan Brave browser cache."""
    return scan_chromium_cache("brave")