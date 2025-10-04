#!/usr/bin/env python3
"""
Chrome browser cache discovery and management for LazyScan.
"""

import os
import sys
import shutil
import asyncio
from typing import Dict, Any

from ..core.logging_config import get_logger
from ..core.formatting import human_readable, get_terminal_colors
from ..core.ui import knight_rider_animation, get_console
from helpers.chrome_cache_helpers import scan_chrome_cache as scan_chrome_cache_helper


logger = get_logger(__name__)
console = get_console()


class ChromePlugin:
    """Plugin for Chrome browser cache discovery and management."""

    @property
    def name(self) -> str:
        return "chrome"

    @property
    def description(self) -> str:
        return "Chrome browser cache discovery and management"

    def scan(self, **kwargs) -> Dict[str, Any]:
        """Perform Chrome-specific scanning."""
        try:
            from helpers.chrome_cache_helpers import scan_chrome_cache as scan_chrome_cache_helper

            # Scan Chrome cache
            result = scan_chrome_cache_helper()

            return {
                "status": "success",
                "cache_info": result,
                "total_size": result.get("total_size", 0) if isinstance(result, dict) else 0
            }

        except Exception as e:
            logger.error(f"Chrome scan failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "total_size": 0
            }

    def clean(self, **kwargs) -> Dict[str, Any]:
        """Perform Chrome-specific cleaning."""
        try:
            from helpers.secure_operations import secure_delete
            from helpers.chrome_cache_helpers import scan_chrome_cache as scan_chrome_cache_helper
            from ..core.ui import knight_rider_animation, get_console
            from ..core.formatting import get_terminal_colors, human_readable

            console = get_console()
            colors = get_terminal_colors()
            CYAN, MAGENTA, YELLOW, RESET, BOLD, BRIGHT_CYAN, BRIGHT_MAGENTA, GREEN, RED = colors[:9]

            # Get Chrome cache report
            report = scan_chrome_cache_helper(include_profiles=True)

            if not report["installed"]:
                return {
                    "status": "error",
                    "message": "Chrome is not installed or not found",
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
                    "message": "No safe Chrome cache items to clean",
                    "cleaned_items": 0,
                    "total_size": 0
                }

            # Extract paths for secure deletion
            paths_to_clean = [path for path, size, item_type in items_to_clean]

            # Show cleaning animation
            console.print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}CHROME CLEAN{CYAN}]{RESET} {YELLOW}Cleaning Chrome cache...{RESET}")
            knight_rider_animation("Purging Chrome cache...", colors=colors[:5])

            # Use secure deletion
            result = secure_delete(paths_to_clean, "Chrome Cache Cleanup")

            # Clear animation
            import sys
            sys.stdout.write("\r" + " " * 100 + "\r")
            sys.stdout.flush()

            if result.success:
                console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}✓{CYAN}]{RESET} {BRIGHT_CYAN}CHROME CACHE CLEANED{RESET}")
                console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Space reclaimed:{RESET} {BRIGHT_MAGENTA}{human_readable(result.size_processed)}{RESET}")
                console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Items cleaned:{RESET} {BRIGHT_CYAN}{result.files_processed}{RESET}")

                if result.errors:
                    console.print(f"{BOLD}{CYAN}[{RED}!{CYAN}]{RESET} {RED}Failed to clean {len(result.errors)} items{RESET}")

                return {
                    "status": "success",
                    "message": "Chrome cache cleaned successfully",
                    "cleaned_items": result.files_processed,
                    "total_size": result.size_processed,
                    "errors": result.errors
                }
            else:
                return {
                    "status": "error",
                    "message": f"Chrome cleaning failed: {result.message}",
                    "cleaned_items": result.files_processed,
                    "total_size": result.size_processed,
                    "errors": result.errors
                }

        except Exception as e:
            logger.error(f"Chrome clean failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "cleaned_items": 0,
                "total_size": 0
            }

    async def scan_async(self, **kwargs) -> Dict[str, Any]:
        """Perform Chrome-specific scanning asynchronously."""
        # Delegate to sync implementation since Chrome scanning is I/O bound
        return await asyncio.get_event_loop().run_in_executor(None, self.scan, **kwargs)

    async def clean_async(self, **kwargs) -> Dict[str, Any]:
        """Perform Chrome-specific cleaning asynchronously."""
        # Delegate to sync implementation since Chrome cleaning involves filesystem operations
        return await asyncio.get_event_loop().run_in_executor(None, self.clean, **kwargs)


# Chrome-specific paths for targeted cleaning
CHROME_PATHS = [
    # Chrome Cache
    os.path.expanduser("~/Library/Caches/Google/Chrome/*"),
    os.path.expanduser("~/Library/Application Support/Google/Chrome/Default/Cache/*"),
    os.path.expanduser(
        "~/Library/Application Support/Google/Chrome/Default/Code Cache/*"
    ),
    os.path.expanduser(
        "~/Library/Application Support/Google/Chrome/Default/GPUCache/*"
    ),
    os.path.expanduser(
        "~/Library/Application Support/Google/Chrome/Default/Service Worker/CacheStorage/*"
    ),
    os.path.expanduser(
        "~/Library/Application Support/Google/Chrome/Default/Service Worker/ScriptCache/*"
    ),
    # Chrome Profile Data (be careful with these)
    os.path.expanduser("~/Library/Application Support/Google/Chrome/*/Cache/*"),
    os.path.expanduser("~/Library/Application Support/Google/Chrome/*/Code Cache/*"),
    os.path.expanduser("~/Library/Application Support/Google/Chrome/*/GPUCache/*"),
    # Chrome Media Cache
    os.path.expanduser(
        "~/Library/Application Support/Google/Chrome/Default/Media Cache/*"
    ),
    os.path.expanduser("~/Library/Application Support/Google/Chrome/*/Media Cache/*"),
    # Chrome Temporary Downloads
    os.path.expanduser(
        "~/Library/Application Support/Google/Chrome/Default/.com.google.Chrome.*"
    ),
    # Old Chrome Versions and Updates
    os.path.expanduser("~/Library/Application Support/Google/Chrome/CrashReports/*"),
    os.path.expanduser(
        "~/Library/Application Support/Google/Chrome/Crashpad/completed/*"
    ),
]


def handle_chrome_discovery(args) -> None:
    """Handle the discovery and processing of Chrome cache using the new helper."""
    if sys.platform != "darwin":
        logger.warning(
            "Chrome cleanup attempted on non-macOS platform",
            extra={"platform": sys.platform},
        )
        console.print("\nError: --chrome option is only available on macOS.")
        return

    # Setup colors
    colors = get_terminal_colors()
    CYAN, MAGENTA, YELLOW, RESET, BOLD, BRIGHT_CYAN, BRIGHT_MAGENTA, GREEN, RED = (
        colors[:9]
    )

    logger.info(
        "Starting Chrome cache discovery and cleanup",
        extra={"operation": "chrome_discovery"},
    )

    console.print(
        f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}CHROME SCANNER{CYAN}]{RESET} {YELLOW}Discovering Chrome profiles and cache...{RESET}"
    )

    # Get Chrome cache report
    try:
        report = scan_chrome_cache_helper(include_profiles=True)
        logger.info(
            "Chrome cache report generated",
            extra={
                "installed": report["installed"],
                "total_size": report.get("total_size", 0),
                "profile_count": len(report.get("profiles", [])),
            },
        )
    except Exception as e:
        logger.error(
            "Chrome cache analysis failed", extra={"error": str(e)}, exc_info=e
        )
        console.print(
            f"{BOLD}{CYAN}[{RED}!{CYAN}]{RESET} {RED}Chrome cache analysis failed: {str(e)}{RESET}"
        )
        return

    if not report["installed"]:
        console.print(
            f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}Chrome is not installed or Application Support folder not found.{RESET}"
        )
        logger.warning("Chrome not installed or not found")
        return

    # Display overview
    console.print(
        f"\n{BOLD}{MAGENTA}┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓{RESET}"
    )
    console.print(
        f"{BOLD}{MAGENTA}┃ {YELLOW}CHROME CACHE ANALYSIS {CYAN}:: {BRIGHT_MAGENTA}TOTAL: {BRIGHT_CYAN}{human_readable(report['total_size']):<10}{MAGENTA} ┃{RESET}"
    )
    console.print(
        f"{BOLD}{MAGENTA}┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛{RESET}"
    )

    # Show profile information
    if report["profiles"]:
        console.print(
            f"\n{BOLD}{CYAN}[{YELLOW}PROFILES{CYAN}]{RESET} {GREEN}Found {len(report['profiles'])} Chrome profiles{RESET}"
        )
        logger.info(
            "Chrome profiles found", extra={"profile_count": len(report["profiles"])}
        )

        for profile in report["profiles"][:5]:  # Show max 5 profiles
            console.print(
                f"  {CYAN}•{RESET} {profile['name']}: {BRIGHT_MAGENTA}{human_readable(profile['total_size'])}{RESET}"
            )
        if len(report["profiles"]) > 5:
            console.print(f"  {CYAN}...and {len(report['profiles']) - 5} more{RESET}")

    # Display safe-to-delete categories
    console.print(
        f"\n{BOLD}{CYAN}[{GREEN}SAFE TO DELETE{CYAN}]{RESET} {GREEN}({human_readable(report['safe_size'])}){RESET}"
    )
    console.print(f"{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")

    safe_categories = {}
    idx = 1
    for category_name, items in report["categories"]["safe"].items():
        if items:
            category_size = sum(size for _, size, _ in items)
            safe_categories[str(idx)] = (category_name, items, category_size)
            console.print(
                f"\n{CYAN}[{idx}]{RESET} {BRIGHT_CYAN}{category_name}:{RESET} {BRIGHT_MAGENTA}{human_readable(category_size)}{RESET}"
            )
            # Show top 3 items
            for path, size, _ in sorted(items, key=lambda x: x[1], reverse=True)[:3]:
                display_path = path.replace(report["chrome_base"] + "/", "")
                if len(display_path) > 55:
                    display_path = "..." + display_path[-52:]
                console.print(
                    f"  {GREEN}→{RESET} {human_readable(size):>10} {YELLOW}{display_path}{RESET}"
                )
            if len(items) > 3:
                console.print(f"  {CYAN}...and {len(items) - 3} more items{RESET}")
            idx += 1

    # Show preserved data
    if report["unsafe_size"] > 0:
        console.print(
            f"\n{BOLD}{CYAN}[{RED}PRESERVE{CYAN}]{RESET} {RED}({human_readable(report['unsafe_size'])}){RESET}"
        )
        console.print(f"{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        for category_name, items in report["categories"]["unsafe"].items():
            if items:
                category_size = sum(size for _, size, _ in items)
                console.print(
                    f"  {RED}{category_name}:{RESET} {BRIGHT_MAGENTA}{human_readable(category_size)}{RESET} {YELLOW}(User data){RESET}"
                )

    # Interactive selection
    console.print(
        f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}?{CYAN}]{RESET} {YELLOW}Select items to clean:{RESET}"
    )
    console.print(f"  {CYAN}a{RESET} - All safe categories")
    console.print(f"  {CYAN}q{RESET} - Quit without cleaning")
    if idx > 1:
        console.print(
            f"  {CYAN}1-{idx - 1}{RESET} - Individual categories (comma-separated)"
        )

    selection = input(f"\n{YELLOW}Your choice:{RESET} ").strip().lower()

    logger.info(
        "User made Chrome cleanup selection",
        extra={"selection": selection, "available_categories": idx - 1},
    )

    if selection == "q":
        console.print(
            f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}Chrome cleanup cancelled.{RESET}"
        )
        logger.info("Chrome cleanup cancelled by user")
        return

    # Determine items to clean
    items_to_clean = []
    if selection == "a":
        logger.info("User selected all safe Chrome categories for cleanup")
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

            logger.info(
                "User selected specific Chrome categories",
                extra={"selected_indices": selected_indices},
            )
        except (ValueError, KeyError) as e:
            console.print(
                f"{BOLD}{CYAN}[{RED}!{CYAN}]{RESET} {RED}Invalid selection.{RESET}"
            )
            logger.error(
                "Invalid Chrome category selection",
                extra={"selection": selection, "error": str(e)},
            )
            return

    if not items_to_clean:
        console.print(
            f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}No items selected.{RESET}"
        )
        logger.warning("No Chrome items selected for cleanup")
        return

    # Calculate total to clean
    total_to_clean = sum(size for _, size, _ in items_to_clean)

    logger.info(
        "Chrome cleanup prepared",
        extra={"item_count": len(items_to_clean), "total_size": total_to_clean},
    )

    # Confirm
    console.print(
        f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}?{CYAN}]{RESET} {YELLOW}Delete {BRIGHT_CYAN}{len(items_to_clean)}{YELLOW} items ({BRIGHT_MAGENTA}{human_readable(total_to_clean)}{YELLOW})? {BRIGHT_CYAN}[y/N]{RESET}: ",
        end="",
        flush=True,
    )

    if input().strip().lower() != "y":
        console.print(
            f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}Chrome cleanup cancelled.{RESET}"
        )
        logger.info("Chrome cleanup cancelled at confirmation")
        return

    # Clean
    console.print(
        f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}►{CYAN}]{RESET} {BRIGHT_CYAN}CLEANING CHROME CACHE...{RESET}"
    )

    logger.info(
        "Starting Chrome cache cleanup",
        extra={"item_count": len(items_to_clean), "total_size": total_to_clean},
    )

    knight_rider_animation("Purging Chrome cache...", colors=colors[:5])

    freed_bytes = 0
    errors = 0

    for path, size, item_type in items_to_clean:
        try:
            logger.debug(
                "Deleting Chrome cache item",
                extra={"path": path, "size": size, "type": item_type},
            )

            if item_type == "dir" and os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            elif item_type == "file" and os.path.isfile(path):
                os.remove(path)
            freed_bytes += size

        except (OSError, PermissionError) as e:
            errors += 1
            logger.warning(
                "Failed to delete Chrome cache item",
                extra={"path": path, "error": str(e)},
            )

    # Clear animation
    sys.stdout.write("\r" + " " * 100 + "\r")
    sys.stdout.flush()

    # Results
    console.print(
        f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}✓{CYAN}]{RESET} {BRIGHT_CYAN}CHROME CACHE CLEANED{RESET}"
    )
    console.print(
        f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Space reclaimed:{RESET} {BRIGHT_MAGENTA}{human_readable(freed_bytes)}{RESET}"
    )
    console.print(
        f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Items cleaned:{RESET} {BRIGHT_CYAN}{len(items_to_clean) - errors}{RESET}"
    )

    if errors > 0:
        console.print(
            f"{BOLD}{CYAN}[{RED}!{CYAN}]{RESET} {RED}Failed to clean {errors} items{RESET}"
        )

    console.print(
        f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}■{CYAN}]{RESET} {GREEN}Chrome cleanup completed!{RESET}"
    )

    logger.info(
        "Chrome cache cleanup completed",
        extra={
            "freed_bytes": freed_bytes,
            "items_cleaned": len(items_to_clean) - errors,
            "errors": errors,
        },
    )
