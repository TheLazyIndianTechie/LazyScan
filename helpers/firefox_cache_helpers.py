#!/usr/bin/env python3
"""
Firefox cache discovery and management helpers for LazyScan.

Provides utilities for Firefox profile enumeration, cache directory identification,
and safe cache cleanup operations aligned with SAFE_TO_DELETE taxonomy.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Iterator, NamedTuple, Tuple

import platformdirs

from lazyscan.core.logging_config import get_logger

logger = get_logger(__name__)


class BrowserProfile(NamedTuple):
    """Represents a browser profile with its cache directories."""
    name: str
    path: Path
    caches: List[Path]


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


def scan_firefox_cache(include_profiles: bool = False) -> Dict[str, Any]:
    """
    Scan Firefox cache and profiles.

    Args:
        include_profiles: Whether to include detailed profile information

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
        "firefox_base": ""
    }

    try:
        # Use platformdirs to get Firefox data directory
        firefox_data_dir = Path(platformdirs.user_data_dir("firefox", "Mozilla"))
        result["firefox_base"] = str(firefox_data_dir)

        # Check if Firefox is installed
        if not firefox_data_dir.exists():
            logger.debug(f"Firefox data directory not found: {firefox_data_dir}")
            return result

        result["installed"] = True

        # Discover profiles
        profiles = list(discover_firefox_profiles())

        if include_profiles:
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

                    # Add to safe items (all Firefox caches are considered safe to delete)
                    safe_items.append((str(cache_dir), size, "dir"))

        # Organize by category
        result["categories"]["safe"]["Cache Directories"] = safe_items
        result["categories"]["unsafe"] = {}  # Firefox caches are all safe to delete

    except Exception as e:
        logger.error(f"Firefox cache scan failed: {e}")
        result["error"] = str(e)

    return result


def discover_firefox_profiles() -> Iterator[BrowserProfile]:
    """
    Discover Firefox profiles across platforms using platformdirs.

    Yields:
        BrowserProfile instances for each discovered profile
    """
    # Use platformdirs to get Firefox data directory
    firefox_data_dir = Path(platformdirs.user_data_dir("firefox", "Mozilla"))

    # Check if Firefox is installed
    if not firefox_data_dir.exists():
        logger.debug(f"Firefox data directory not found: {firefox_data_dir}")
        return

    # Look for profiles.ini
    profiles_ini = firefox_data_dir / "profiles.ini"
    if profiles_ini.exists():
        yield from _parse_profiles_ini(profiles_ini, firefox_data_dir)
    else:
        # Fallback: scan for profile directories
        profiles_dir = firefox_data_dir / "Profiles"
        if profiles_dir.exists():
            for profile_dir in profiles_dir.iterdir():
                if profile_dir.is_dir() and _is_valid_firefox_profile(profile_dir):
                    caches = _get_firefox_cache_dirs(profile_dir)
                    yield BrowserProfile(
                        name=profile_dir.name,
                        path=profile_dir,
                        caches=caches
                    )


def _parse_profiles_ini(profiles_ini: Path, base_dir: Path) -> Iterator[BrowserProfile]:
    """Parse Firefox profiles.ini to extract profile information."""
    current_profile = None
    current_path = None

    try:
        with open(profiles_ini, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("Path="):
                    rel_path = line.split("=", 1)[1].strip()
                    # Handle relative paths
                    if not Path(rel_path).is_absolute():
                        current_path = base_dir / rel_path
                    else:
                        current_path = Path(rel_path)

                elif line.startswith("Name=") and current_path:
                    profile_name = line.split("=", 1)[1].strip()
                    if current_path.exists() and _is_valid_firefox_profile(current_path):
                        caches = _get_firefox_cache_dirs(current_path)
                        yield BrowserProfile(
                            name=profile_name,
                            path=current_path,
                            caches=caches
                        )
                    current_path = None

    except Exception as e:
        logger.warning(f"Failed to parse profiles.ini: {e}")


def _is_valid_firefox_profile(profile_dir: Path) -> bool:
    """Check if a directory contains valid Firefox profile markers."""
    markers = ["places.sqlite", "prefs.js", "compatibility.ini"]
    return any((profile_dir / marker).exists() for marker in markers)


def _get_firefox_cache_dirs(profile_dir: Path) -> List[Path]:
    """Get SAFE_TO_DELETE cache directories for a Firefox profile."""
    cache_dirs = []

    # Firefox cache directories that are safe to delete
    safe_cache_dirs = ["cache2", "startupCache", "shader-cache"]

    for cache_name in safe_cache_dirs:
        cache_path = profile_dir / cache_name
        if cache_path.exists():
            cache_dirs.append(cache_path)

    return cache_dirs


def get_firefox_cache_targets(profile_path: str | None = None) -> Dict[str, str]:
    """
    Returns a dictionary of cache target directories for Firefox.

    Args:
        profile_path: Path to a specific Firefox profile. If None, discovers all profiles.

    Returns:
        Dictionary mapping cache category names to their paths.
    """
    cache_targets = {}

    if profile_path:
        # Specific profile provided
        profile_dir = Path(profile_path)
        if profile_dir.exists() and _is_valid_firefox_profile(profile_dir):
            caches = _get_firefox_cache_dirs(profile_dir)
            for cache_dir in caches:
                cache_targets[cache_dir.name] = str(cache_dir)
    else:
        # Discover all profiles
        for profile in discover_firefox_profiles():
            for cache_dir in profile.caches:
                cache_targets[f"{profile.name}:{cache_dir.name}"] = str(cache_dir)

    return cache_targets