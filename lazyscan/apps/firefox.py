#!/usr/bin/env python3
"""
Firefox browser cache discovery and management for LazyScan.

Implements Firefox-specific profile enumeration via profiles.ini parsing,
cache directory identification aligned with SAFE_TO_DELETE taxonomy,
and cross-platform profile discovery using platformdirs.
"""

import os
import sys
import glob
from pathlib import Path
from typing import List, Dict, Any, Iterator, NamedTuple

import platformdirs

from ..core.logging_config import get_logger
from ..core.formatting import human_readable, get_terminal_colors
from ..core.ui import knight_rider_animation, get_console

logger = get_logger(__name__)
console = get_console()


class BrowserProfile(NamedTuple):
    """Represents a browser profile with its cache directories."""
    name: str
    path: Path
    caches: List[Path]


class FirefoxPlugin:
    """Plugin for Firefox browser cache discovery and management."""

    @property
    def name(self) -> str:
        return "firefox"

    @property
    def description(self) -> str:
        return "Firefox browser cache discovery and management"

    def scan(self, **kwargs) -> Dict[str, Any]:
        """Perform Firefox-specific scanning."""
        try:
            from helpers.firefox_cache_helpers import scan_firefox_cache

            # Scan Firefox cache
            result = scan_firefox_cache()

            return {
                "status": "success",
                "cache_info": result,
                "total_size": result.get("total_size", 0) if isinstance(result, dict) else 0
            }

        except Exception as e:
            logger.error(f"Firefox scan failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "total_size": 0
            }

    def clean(self, **kwargs) -> Dict[str, Any]:
        """Perform Firefox-specific cleaning."""
        try:
            from helpers.secure_operations import secure_delete
            from helpers.firefox_cache_helpers import scan_firefox_cache
            from ..core.ui import knight_rider_animation, get_console
            from ..core.formatting import get_terminal_colors, human_readable

            console = get_console()
            colors = get_terminal_colors()
            CYAN, MAGENTA, YELLOW, RESET, BOLD, BRIGHT_CYAN, BRIGHT_MAGENTA, GREEN, RED = colors[:9]

            # Get Firefox cache report
            report = scan_firefox_cache(include_profiles=True)

            if not report["installed"]:
                return {
                    "status": "error",
                    "message": "Firefox is not installed or not found",
                    "cleaned_items": 0,
                    "total_size": 0
                }

            # Get items to clean - use safe categories by default
            items_to_clean = []
            for category_name, items in report["categories"]["safe"].items():
                items_to_clean.extend(items)

            if not items_to_clean:
                return {
                    "status": "success",
                    "message": "No safe Firefox cache items to clean",
                    "cleaned_items": 0,
                    "total_size": 0
                }

            # Extract paths for secure deletion
            paths_to_clean = [path for path, size, item_type in items_to_clean]

            # Show cleaning animation
            console.print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}FIREFOX CLEAN{CYAN}]{RESET} {YELLOW}Cleaning Firefox cache...{RESET}")
            knight_rider_animation("Purging Firefox cache...", colors=colors[:5])

            # Use secure deletion
            result = secure_delete(paths_to_clean, "Firefox Cache Cleanup")

            # Clear animation
            import sys
            sys.stdout.write("\r" + " " * 100 + "\r")
            sys.stdout.flush()

            if result.success:
                console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}✓{CYAN}]{RESET} {BRIGHT_CYAN}FIREFOX CACHE CLEANED{RESET}")
                console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Space reclaimed:{RESET} {BRIGHT_MAGENTA}{human_readable(result.size_processed)}{RESET}")
                console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Items cleaned:{RESET} {BRIGHT_CYAN}{result.files_processed}{RESET}")

                if result.errors:
                    console.print(f"{BOLD}{CYAN}[{RED}!{CYAN}]{RESET} {RED}Failed to clean {len(result.errors)} items{RESET}")

                return {
                    "status": "success",
                    "message": "Firefox cache cleaned successfully",
                    "cleaned_items": result.files_processed,
                    "total_size": result.size_processed,
                    "errors": result.errors
                }
            else:
                return {
                    "status": "error",
                    "message": f"Firefox cleaning failed: {result.message}",
                    "cleaned_items": result.files_processed,
                    "total_size": result.size_processed,
                    "errors": result.errors
                }

        except Exception as e:
            logger.error(f"Firefox clean failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "cleaned_items": 0,
                "total_size": 0
            }


# Firefox-specific paths for targeted cleaning
FIREFOX_PATHS = [
    # Firefox Cache (platform-specific)
]


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


def handle_firefox_discovery(args) -> None:
    """Handle the discovery and processing of Firefox cache using the new helper."""
    # Setup colors
    colors = get_terminal_colors()
    CYAN, MAGENTA, YELLOW, RESET, BOLD, BRIGHT_CYAN, BRIGHT_MAGENTA, GREEN, RED = colors[:9]

    logger.info("Starting Firefox cache discovery", extra={"operation": "firefox_discovery"})

    console.print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}FIREFOX SCANNER{CYAN}]{RESET} {YELLOW}Discovering Firefox profiles and cache...{RESET}")

    # Get Firefox cache report
    try:
        from helpers.firefox_cache_helpers import scan_firefox_cache
        report = scan_firefox_cache(include_profiles=True)
        logger.info("Firefox cache report generated", extra={
            "installed": report["installed"],
            "total_size": report.get("total_size", 0),
            "profile_count": len(report.get("profiles", []))
        })
    except Exception as e:
        logger.error("Firefox cache analysis failed", extra={"error": str(e)}, exc_info=e)
        console.print(f"{BOLD}{CYAN}[{RED}!{CYAN}]{RESET} {RED}Firefox cache analysis failed: {str(e)}{RESET}")
        return

    if not report["installed"]:
        console.print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}Firefox is not installed or profiles not found.{RESET}")
        logger.warning("Firefox not installed or not found")
        return

    # Display overview
    console.print(f"\n{BOLD}{MAGENTA}┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓{RESET}")
    console.print(f"{BOLD}{MAGENTA}┃ {YELLOW}FIREFOX CACHE ANALYSIS {CYAN}:: {BRIGHT_MAGENTA}TOTAL: {BRIGHT_CYAN}{human_readable(report['total_size']):<10}{MAGENTA} ┃{RESET}")
    console.print(f"{BOLD}{MAGENTA}┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛{RESET}")

    # Show profile information
    if report["profiles"]:
        console.print(f"\n{BOLD}{CYAN}[{YELLOW}PROFILES{CYAN}]{RESET} {GREEN}Found {len(report['profiles'])} Firefox profiles{RESET}")
        logger.info("Firefox profiles found", extra={"profile_count": len(report["profiles"])})

        for profile in report["profiles"][:5]:  # Show max 5 profiles
            console.print(f"  {CYAN}•{RESET} {profile['name']}: {BRIGHT_MAGENTA}{human_readable(profile['total_size'])}{RESET}")
        if len(report["profiles"]) > 5:
            console.print(f"  {CYAN}...and {len(report['profiles']) - 5} more{RESET}")

    # Display safe-to-delete categories
    console.print(f"\n{BOLD}{CYAN}[{GREEN}SAFE TO DELETE{CYAN}]{RESET} {GREEN}({human_readable(report['safe_size'])}){RESET}")
    console.print(f"{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")

    safe_categories = {}
    idx = 1
    for category_name, items in report["categories"]["safe"].items():
        if items:
            category_size = sum(size for _, size, _ in items)
            safe_categories[str(idx)] = (category_name, items, category_size)
            console.print(f"\n{CYAN}[{idx}]{RESET} {BRIGHT_CYAN}{category_name}:{RESET} {BRIGHT_MAGENTA}{human_readable(category_size)}{RESET}")
            # Show top 3 items
            for path, size, _ in sorted(items, key=lambda x: x[1], reverse=True)[:3]:
                display_path = path.replace(report["firefox_base"] + "/", "")
                if len(display_path) > 55:
                    display_path = "..." + display_path[-52:]
                console.print(f"  {GREEN}→{RESET} {human_readable(size):>10} {YELLOW}{display_path}{RESET}")
            if len(items) > 3:
                console.print(f"  {CYAN}...and {len(items) - 3} more items{RESET}")
            idx += 1

    # Show preserved data
    if report["unsafe_size"] > 0:
        console.print(f"\n{BOLD}{CYAN}[{RED}PRESERVE{CYAN}]{RESET} {RED}({human_readable(report['unsafe_size'])}){RESET}")
        console.print(f"{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        for category_name, items in report["categories"]["unsafe"].items():
            if items:
                category_size = sum(size for _, size, _ in items)
                console.print(f"  {RED}{category_name}:{RESET} {BRIGHT_MAGENTA}{human_readable(category_size)}{RESET} {YELLOW}(User data){RESET}")

    # Interactive selection
    console.print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}?{CYAN}]{RESET} {YELLOW}Select items to clean:{RESET}")
    console.print(f"  {CYAN}a{RESET} - All safe categories")
    console.print(f"  {CYAN}q{RESET} - Quit without cleaning")
    if idx > 1:
        console.print(f"  {CYAN}1-{idx - 1}{RESET} - Individual categories (comma-separated)")

    selection = input(f"\n{YELLOW}Your choice:{RESET} ").strip().lower()

    logger.info("User made Firefox cleanup selection", extra={"selection": selection, "available_categories": idx - 1})

    if selection == "q":
        console.print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}Firefox cleanup cancelled.{RESET}")
        logger.info("Firefox cleanup cancelled by user")
        return

    # Determine items to clean
    items_to_clean = []
    if selection == "a":
        logger.info("User selected all safe Firefox categories for cleanup")
        for category_name, items in report["categories"]["safe"].items():
            items_to_clean.extend(items)
    else:
        try:
            selected_indices = []
            for idx_str in selection.split(","):
                idx_str = idx_str.strip()
                if idx_str in safe_categories:
                    selected_indices.append(idx_str)
                    _, items, _ = safe_categories[idx_str]
                    items_to_clean.extend(items)

            logger.info("User selected specific Firefox categories", extra={"selected_indices": selected_indices})
        except (ValueError, KeyError) as e:
            console.print(f"{BOLD}{CYAN}[{RED}!{CYAN}]{RESET} {RED}Invalid selection.{RESET}")
            logger.error("Invalid Firefox category selection", extra={"selection": selection, "error": str(e)})
            return

    if not items_to_clean:
        console.print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}No items selected.{RESET}")
        logger.warning("No Firefox items selected for cleanup")
        return

    # Calculate total to clean
    total_to_clean = sum(size for _, size, _ in items_to_clean)

    logger.info("Firefox cleanup prepared", extra={"item_count": len(items_to_clean), "total_size": total_to_clean})

    # Confirm
    console.print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}?{CYAN}]{RESET} {YELLOW}Delete {BRIGHT_CYAN}{len(items_to_clean)}{YELLOW} items ({BRIGHT_MAGENTA}{human_readable(total_to_clean)}{YELLOW})? {BRIGHT_CYAN}[y/N]{RESET}: ", end="", flush=True)

    if input().strip().lower() != "y":
        console.print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}Firefox cleanup cancelled.{RESET}")
        logger.info("Firefox cleanup cancelled at confirmation")
        return

    # Clean
    console.print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}►{CYAN}]{RESET} {BRIGHT_CYAN}CLEANING FIREFOX CACHE...{RESET}")

    logger.info("Starting Firefox cache cleanup", extra={"item_count": len(items_to_clean), "total_size": total_to_clean})

    knight_rider_animation("Purging Firefox cache...", colors=colors[:5])

    freed_bytes = 0
    errors = 0

    for path, size, item_type in items_to_clean:
        try:
            logger.debug("Deleting Firefox cache item", extra={"path": path, "size": size, "type": item_type})

            if item_type == "dir" and os.path.isdir(path):
                import shutil
                shutil.rmtree(path, ignore_errors=True)
            elif item_type == "file" and os.path.isfile(path):
                os.remove(path)
            freed_bytes += size

        except (OSError, PermissionError) as e:
            errors += 1
            logger.warning("Failed to delete Firefox cache item", extra={"path": path, "error": str(e)})

    # Clear animation
    sys.stdout.write("\r" + " " * 100 + "\r")
    sys.stdout.flush()

    # Results
    console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}✓{CYAN}]{RESET} {BRIGHT_CYAN}FIREFOX CACHE CLEANED{RESET}")
    console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Space reclaimed:{RESET} {BRIGHT_MAGENTA}{human_readable(freed_bytes)}{RESET}")
    console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Items cleaned:{RESET} {BRIGHT_CYAN}{len(items_to_clean) - errors}{RESET}")

    if errors > 0:
        console.print(f"{BOLD}{CYAN}[{RED}!{CYAN}]{RESET} {RED}Failed to clean {errors} items{RESET}")

    console.print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}■{CYAN}]{RESET} {GREEN}Firefox cleanup completed!{RESET}")

    logger.info("Firefox cache cleanup completed", extra={
        "freed_bytes": freed_bytes,
        "items_cleaned": len(items_to_clean) - errors,
        "errors": errors
    })
