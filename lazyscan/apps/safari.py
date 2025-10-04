# Safari browser cache discovery and management for LazyScan.

import os
import sys
import platform
from pathlib import Path
from typing import List, Dict, Any, Iterator, NamedTuple

from ..core.logging_config import get_logger
from ..core.formatting import human_readable, get_terminal_colors
from ..core.ui import knight_rider_animation, get_console

logger = get_logger(__name__)
console = get_console()


class SafariPlugin:
    """Plugin for Safari browser cache discovery and management."""

    @property
    def name(self) -> str:
        return "safari"

    @property
    def description(self) -> str:
        return "Safari browser cache discovery and management (macOS only)"

    def scan(self, **kwargs) -> Dict[str, Any]:
        """Perform Safari-specific scanning."""
        try:
            from helpers.safari_cache_helpers import scan_safari_cache

            # Check if we're on macOS
            if platform.system() != "Darwin":
                return {
                    "status": "error",
                    "message": "Safari cache scanning is only supported on macOS",
                    "total_size": 0
                }

            # Scan Safari cache
            result = scan_safari_cache()

            return {
                "status": "success",
                "cache_info": result,
                "total_size": result.get("total_size", 0) if isinstance(result, dict) else 0
            }

        except Exception as e:
            logger.error(f"Safari scan failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "total_size": 0
            }

    def clean(self, **kwargs) -> Dict[str, Any]:
        """Perform Safari-specific cleaning."""
        try:
            from helpers.secure_operations import secure_delete
            from helpers.safari_cache_helpers import scan_safari_cache, check_safari_permissions
            from ..core.ui import knight_rider_animation, get_console
            from ..core.formatting import get_terminal_colors, human_readable

            console = get_console()
            colors = get_terminal_colors()
            CYAN, MAGENTA, YELLOW, RESET, BOLD, BRIGHT_CYAN, BRIGHT_MAGENTA, GREEN, RED = colors[:9]

            # Check platform
            if platform.system() != "Darwin":
                return {
                    "status": "error",
                    "message": "Safari cache cleaning is only supported on macOS",
                    "cleaned_items": 0,
                    "total_size": 0
                }

            # Check permissions first
            perm_check = check_safari_permissions()
            if not perm_check["can_access_user_cache"] and not perm_check["can_access_system_cache"]:
                return {
                    "status": "error",
                    "message": "No accessible Safari cache directories found",
                    "cleaned_items": 0,
                    "total_size": 0
                }

            # Get Safari cache report
            report = scan_safari_cache()

            if not report["installed"]:
                return {
                    "status": "error",
                    "message": "Safari cache directories not found",
                    "cleaned_items": 0,
                    "total_size": 0
                }

            # Get items to clean - use safe categories by default
            items_to_clean = []
            for category_name, items in report["categories"]["safe"].items():
                items_to_clean.extend(items)

            # Check for system cache that requires root
            system_items = []
            for category_name, items in report["categories"]["unsafe"].items():
                system_items.extend(items)

            if not items_to_clean and not system_items:
                return {
                    "status": "success",
                    "message": "No Safari cache items to clean",
                    "cleaned_items": 0,
                    "total_size": 0
                }

            # Show permission warnings
            if system_items and not perm_check["is_root"]:
                console.print(f"{BOLD}{YELLOW}[WARNING]{RESET} {YELLOW}Some Safari caches require root privileges{RESET}")
                console.print(f"{YELLOW}Run with 'sudo' to clean system-level Safari caches{RESET}")

            # Extract paths for secure deletion
            paths_to_clean = [path for path, size, item_type in items_to_clean]

            # Show cleaning animation
            console.print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}SAFARI CLEAN{CYAN}]{RESET} {YELLOW}Cleaning Safari cache...{RESET}")
            knight_rider_animation("Purging Safari cache...", colors=colors[:5])

            # Use secure deletion
            result = secure_delete(paths_to_clean, "Safari Cache Cleanup")

            # Clear animation
            import sys
            sys.stdout.write("\r" + " " * 100 + "\r")
            sys.stdout.flush()

            if result.success:
                console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}✓{CYAN}]{RESET} {BRIGHT_CYAN}SAFARI CACHE CLEANED{RESET}")
                console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Space reclaimed:{RESET} {BRIGHT_MAGENTA}{human_readable(result.size_processed)}{RESET}")
                console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Items cleaned:{RESET} {BRIGHT_CYAN}{result.files_processed}{RESET}")

                if result.errors:
                    console.print(f"{BOLD}{CYAN}[{RED}!{CYAN}]{RESET} {RED}Failed to clean {len(result.errors)} items{RESET}")

                return {
                    "status": "success",
                    "message": "Safari cache cleaned successfully",
                    "cleaned_items": result.files_processed,
                    "total_size": result.size_processed,
                    "errors": result.errors
                }
            else:
                return {
                    "status": "error",
                    "message": f"Safari cleaning failed: {result.message}",
                    "cleaned_items": result.files_processed,
                    "total_size": result.size_processed,
                    "errors": result.errors
                }

        except Exception as e:
            logger.error(f"Safari clean failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "cleaned_items": 0,
                "total_size": 0
            }


def handle_safari_discovery(args) -> None:
    """Handle the discovery and processing of Safari cache."""
    # Setup colors
    colors = get_terminal_colors()
    CYAN, MAGENTA, YELLOW, RESET, BOLD, BRIGHT_CYAN, BRIGHT_MAGENTA, GREEN, RED = colors[:9]

    logger.info("Starting Safari cache discovery", extra={"operation": "safari_discovery"})

    console.print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}SAFARI SCANNER{CYAN}]{RESET} {YELLOW}Discovering Safari cache...{RESET}")

    # Check platform
    if platform.system() != "Darwin":
        console.print(f"{BOLD}{CYAN}[{RED}!{CYAN}]{RESET} {RED}Safari cache scanning is only supported on macOS{RESET}")
        logger.warning("Safari scanning attempted on non-macOS platform")
        return

    # Check permissions
    try:
        from helpers.safari_cache_helpers import check_safari_permissions
        perm_check = check_safari_permissions()

        if not perm_check["can_access_user_cache"] and not perm_check["can_access_system_cache"]:
            console.print(f"{BOLD}{CYAN}[{RED}!{CYAN}]{RESET} {RED}No accessible Safari cache directories found{RESET}")
            console.print(f"{YELLOW}Check permissions or run with sudo for system caches{RESET}")
            logger.warning("No accessible Safari cache directories")
            return

        if not perm_check["is_root"] and perm_check["can_access_system_cache"]:
            console.print(f"{BOLD}{YELLOW}[WARNING]{RESET} {YELLOW}System Safari caches detected but running as non-root{RESET}")
            console.print(f"{YELLOW}Run with 'sudo' to access system-level caches{RESET}")

    except Exception as e:
        logger.error("Safari permission check failed", extra={"error": str(e)}, exc_info=e)
        console.print(f"{BOLD}{CYAN}[{RED}!{CYAN}]{RESET} {RED}Safari permission check failed: {str(e)}{RESET}")
        return

    # Get Safari cache report
    try:
        from helpers.safari_cache_helpers import scan_safari_cache
        report = scan_safari_cache()
        logger.info("Safari cache report generated", extra={
            "installed": report["installed"],
            "total_size": report.get("total_size", 0),
            "requires_root": report.get("requires_root", False)
        })
    except Exception as e:
        logger.error("Safari cache analysis failed", extra={"error": str(e)}, exc_info=e)
        console.print(f"{BOLD}{CYAN}[{RED}!{CYAN}]{RESET} {RED}Safari cache analysis failed: {str(e)}{RESET}")
        return

    if not report["installed"]:
        console.print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}Safari cache directories not found.{RESET}")
        logger.warning("Safari cache directories not found")
        return

    # Display overview
    console.print(f"\n{BOLD}{MAGENTA}┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓{RESET}")
    console.print(f"{BOLD}{MAGENTA}┃ {YELLOW}SAFARI CACHE ANALYSIS {CYAN}:: {BRIGHT_MAGENTA}TOTAL: {BRIGHT_CYAN}{human_readable(report['total_size']):<10}{MAGENTA} ┃{RESET}")
    console.print(f"{BOLD}{MAGENTA}┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛{RESET}")

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
                display_path = path.replace(str(Path.home()), "~")
                if len(display_path) > 55:
                    display_path = "..." + display_path[-52:]
                console.print(f"  {GREEN}→{RESET} {human_readable(size):>10} {YELLOW}{display_path}{RESET}")
            if len(items) > 3:
                console.print(f"  {CYAN}...and {len(items) - 3} more items{RESET}")
            idx += 1

    # Show system caches that require root
    if report["unsafe_size"] > 0:
        console.print(f"\n{BOLD}{CYAN}[{RED}REQUIRES ROOT{CYAN}]{RESET} {RED}({human_readable(report['unsafe_size'])}){RESET}")
        console.print(f"{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        for category_name, items in report["categories"]["unsafe"].items():
            if items:
                category_size = sum(size for _, size, _ in items)
                console.print(f"  {RED}{category_name}:{RESET} {BRIGHT_MAGENTA}{human_readable(category_size)}{RESET} {YELLOW}(requires sudo){RESET}")

    # Interactive selection
    if safe_categories:
        console.print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}?{CYAN}]{RESET} {YELLOW}Select items to clean:{RESET}")
        console.print(f"  {CYAN}a{RESET} - All safe categories")
        console.print(f"  {CYAN}q{RESET} - Quit without cleaning")
        if idx > 1:
            console.print(f"  {CYAN}1-{idx - 1}{RESET} - Individual categories (comma-separated)")

        selection = input(f"\n{YELLOW}Your choice:{RESET} ").strip().lower()

        logger.info("User made Safari cleanup selection", extra={"selection": selection, "available_categories": idx - 1})

        if selection == "q":
            console.print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}Safari cleanup cancelled.{RESET}")
            logger.info("Safari cleanup cancelled by user")
            return

        # Determine items to clean
        items_to_clean = []
        if selection == "a":
            logger.info("User selected all safe Safari categories for cleanup")
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

                logger.info("User selected specific Safari categories", extra={"selected_indices": selected_indices})
            except (ValueError, KeyError) as e:
                console.print(f"{BOLD}{CYAN}[{RED}!{CYAN}]{RESET} {RED}Invalid selection.{RESET}")
                logger.error("Invalid Safari category selection", extra={"selection": selection, "error": str(e)})
                return

        if not items_to_clean:
            console.print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}No items selected.{RESET}")
            logger.warning("No Safari items selected for cleanup")
            return

        # Calculate total to clean
        total_to_clean = sum(size for _, size, _ in items_to_clean)

        logger.info("Safari cleanup prepared", extra={"item_count": len(items_to_clean), "total_size": total_to_clean})

        # Confirm
        console.print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}?{CYAN}]{RESET} {YELLOW}Delete {BRIGHT_CYAN}{len(items_to_clean)}{YELLOW} items ({BRIGHT_MAGENTA}{human_readable(total_to_clean)}{YELLOW})? {BRIGHT_CYAN}[y/N]{RESET}: ", end="", flush=True)

        if input().strip().lower() != "y":
            console.print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}Safari cleanup cancelled.{RESET}")
            logger.info("Safari cleanup cancelled at confirmation")
            return

        # Clean
        console.print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}►{CYAN}]{RESET} {BRIGHT_CYAN}CLEANING SAFARI CACHE...{RESET}")

        logger.info("Starting Safari cache cleanup", extra={"item_count": len(items_to_clean), "total_size": total_to_clean})

        knight_rider_animation("Purging Safari cache...", colors=colors[:5])

        freed_bytes = 0
        errors = 0

        for path, size, item_type in items_to_clean:
            try:
                logger.debug("Deleting Safari cache item", extra={"path": path, "size": size, "type": item_type})

                if item_type == "dir" and os.path.isdir(path):
                    import shutil
                    shutil.rmtree(path, ignore_errors=True)
                elif item_type == "file" and os.path.isfile(path):
                    os.remove(path)
                freed_bytes += size

            except (OSError, PermissionError) as e:
                errors += 1
                logger.warning("Failed to delete Safari cache item", extra={"path": path, "error": str(e)})

        # Clear animation
        sys.stdout.write("\r" + " " * 100 + "\r")
        sys.stdout.flush()

        # Results
        console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}✓{CYAN}]{RESET} {BRIGHT_CYAN}SAFARI CACHE CLEANED{RESET}")
        console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Space reclaimed:{RESET} {BRIGHT_MAGENTA}{human_readable(freed_bytes)}{RESET}")
        console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Items cleaned:{RESET} {BRIGHT_CYAN}{len(items_to_clean) - errors}{RESET}")

        if errors > 0:
            console.print(f"{BOLD}{CYAN}[{RED}!{CYAN}]{RESET} {RED}Failed to clean {errors} items{RESET}")

        console.print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}■{CYAN}]{RESET} {GREEN}Safari cleanup completed!{RESET}")

        logger.info("Safari cache cleanup completed", extra={
            "freed_bytes": freed_bytes,
            "items_cleaned": len(items_to_clean) - errors,
            "errors": errors
        })
    else:
        console.print(f"\n{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}No safe Safari cache items available for cleanup.{RESET}")
        if report["unsafe_size"] > 0:
            console.print(f"{YELLOW}System caches require root privileges (try with sudo).{RESET}")
        logger.info("No safe Safari cache items available")