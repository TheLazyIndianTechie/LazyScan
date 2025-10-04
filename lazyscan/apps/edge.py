# Microsoft Edge browser cache discovery and management for LazyScan.

import os
import sys
from typing import List, Dict, Any

from ..core.logging_config import get_logger
from ..core.formatting import human_readable, get_terminal_colors
from ..core.ui import knight_rider_animation, get_console

logger = get_logger(__name__)
console = get_console()


class EdgePlugin:
    """Plugin for Microsoft Edge browser cache discovery and management."""

    @property
    def name(self) -> str:
        return "edge"

    @property
    def description(self) -> str:
        return "Microsoft Edge browser cache discovery and management"

    def scan(self, **kwargs) -> Dict[str, Any]:
        """Perform Edge-specific scanning."""
        try:
            from helpers.chromium_cache_helpers import scan_edge_cache

            # Scan Edge cache
            result = scan_edge_cache()

            return {
                "status": "success",
                "cache_info": result,
                "total_size": result.get("total_size", 0) if isinstance(result, dict) else 0
            }

        except Exception as e:
            logger.error(f"Edge scan failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "total_size": 0
            }

    def clean(self, **kwargs) -> Dict[str, Any]:
        """Perform Edge-specific cleaning."""
        try:
            from helpers.secure_operations import secure_delete
            from helpers.chromium_cache_helpers import scan_edge_cache
            from ..core.ui import knight_rider_animation, get_console
            from ..core.formatting import get_terminal_colors, human_readable

            console = get_console()
            colors = get_terminal_colors()
            CYAN, MAGENTA, YELLOW, RESET, BOLD, BRIGHT_CYAN, BRIGHT_MAGENTA, GREEN, RED = colors[:9]

            # Get Edge cache report
            report = scan_edge_cache()

            if not report["installed"]:
                return {
                    "status": "error",
                    "message": "Microsoft Edge is not installed or not found",
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
                    "message": "No safe Microsoft Edge cache items to clean",
                    "cleaned_items": 0,
                    "total_size": 0
                }

            # Extract paths for secure deletion
            paths_to_clean = [path for path, size, item_type in items_to_clean]

            # Show cleaning animation
            console.print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}EDGE CLEAN{CYAN}]{RESET} {YELLOW}Cleaning Microsoft Edge cache...{RESET}")
            knight_rider_animation("Purging Edge cache...", colors=colors[:5])

            # Use secure deletion
            result = secure_delete(paths_to_clean, "Edge Cache Cleanup")

            # Clear animation
            import sys
            sys.stdout.write("\r" + " " * 100 + "\r")
            sys.stdout.flush()

            if result.success:
                console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}✓{CYAN}]{RESET} {BRIGHT_CYAN}EDGE CACHE CLEANED{RESET}")
                console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Space reclaimed:{RESET} {BRIGHT_MAGENTA}{human_readable(result.size_processed)}{RESET}")
                console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Items cleaned:{RESET} {BRIGHT_CYAN}{result.files_processed}{RESET}")

                if result.errors:
                    console.print(f"{BOLD}{CYAN}[{RED}!{CYAN}]{RESET} {RED}Failed to clean {len(result.errors)} items{RESET}")

                return {
                    "status": "success",
                    "message": "Microsoft Edge cache cleaned successfully",
                    "cleaned_items": result.files_processed,
                    "total_size": result.size_processed,
                    "errors": result.errors
                }
            else:
                return {
                    "status": "error",
                    "message": f"Edge cleaning failed: {result.message}",
                    "cleaned_items": result.files_processed,
                    "total_size": result.size_processed,
                    "errors": result.errors
                }

        except Exception as e:
            logger.error(f"Edge clean failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "cleaned_items": 0,
                "total_size": 0
            }


def handle_edge_discovery(args) -> None:
    """Handle the discovery and processing of Microsoft Edge cache."""
    # Setup colors
    colors = get_terminal_colors()
    CYAN, MAGENTA, YELLOW, RESET, BOLD, BRIGHT_CYAN, BRIGHT_MAGENTA, GREEN, RED = colors[:9]

    logger.info("Starting Microsoft Edge cache discovery", extra={"operation": "edge_discovery"})

    console.print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}EDGE SCANNER{CYAN}]{RESET} {YELLOW}Discovering Microsoft Edge profiles and cache...{RESET}")

    # Get Edge cache report
    try:
        from helpers.chromium_cache_helpers import scan_edge_cache
        report = scan_edge_cache()
        logger.info("Edge cache report generated", extra={
            "installed": report["installed"],
            "total_size": report.get("total_size", 0),
            "profile_count": len(report.get("profiles", []))
        })
    except Exception as e:
        logger.error("Edge cache analysis failed", extra={"error": str(e)}, exc_info=e)
        console.print(f"{BOLD}{CYAN}[{RED}!{CYAN}]{RESET} {RED}Edge cache analysis failed: {str(e)}{RESET}")
        return

    if not report["installed"]:
        console.print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}Microsoft Edge is not installed or profiles not found.{RESET}")
        logger.warning("Edge not installed or not found")
        return

    # Display overview
    console.print(f"\n{BOLD}{MAGENTA}┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓{RESET}")
    console.print(f"{BOLD}{MAGENTA}┃ {YELLOW}EDGE CACHE ANALYSIS {CYAN}:: {BRIGHT_MAGENTA}TOTAL: {BRIGHT_CYAN}{human_readable(report['total_size']):<10}{MAGENTA} ┃{RESET}")
    console.print(f"{BOLD}{MAGENTA}┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛{RESET}")

    # Show profile information
    if report["profiles"]:
        console.print(f"\n{BOLD}{CYAN}[{YELLOW}PROFILES{CYAN}]{RESET} {GREEN}Found {len(report['profiles'])} Edge profiles{RESET}")
        logger.info("Edge profiles found", extra={"profile_count": len(report["profiles"])})

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
                display_path = path.replace(report["data_dir"] + "/", "")
                if len(display_path) > 55:
                    display_path = "..." + display_path[-52:]
                console.print(f"  {GREEN}→{RESET} {human_readable(size):>10} {YELLOW}{display_path}{RESET}")
            if len(items) > 3:
                console.print(f"  {CYAN}...and {len(items) - 3} more items{RESET}")
            idx += 1

    # Interactive selection
    console.print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}?{CYAN}]{RESET} {YELLOW}Select items to clean:{RESET}")
    console.print(f"  {CYAN}a{RESET} - All safe categories")
    console.print(f"  {CYAN}q{RESET} - Quit without cleaning")
    if idx > 1:
        console.print(f"  {CYAN}1-{idx - 1}{RESET} - Individual categories (comma-separated)")

    selection = input(f"\n{YELLOW}Your choice:{RESET} ").strip().lower()

    logger.info("User made Edge cleanup selection", extra={"selection": selection, "available_categories": idx - 1})

    if selection == "q":
        console.print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}Edge cleanup cancelled.{RESET}")
        logger.info("Edge cleanup cancelled by user")
        return

    # Determine items to clean
    items_to_clean = []
    if selection == "a":
        logger.info("User selected all safe Edge categories for cleanup")
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

            logger.info("User selected specific Edge categories", extra={"selected_indices": selected_indices})
        except (ValueError, KeyError) as e:
            console.print(f"{BOLD}{CYAN}[{RED}!{CYAN}]{RESET} {RED}Invalid selection.{RESET}")
            logger.error("Invalid Edge category selection", extra={"selection": selection, "error": str(e)})
            return

    if not items_to_clean:
        console.print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}No items selected.{RESET}")
        logger.warning("No Edge items selected for cleanup")
        return

    # Calculate total to clean
    total_to_clean = sum(size for _, size, _ in items_to_clean)

    logger.info("Edge cleanup prepared", extra={"item_count": len(items_to_clean), "total_size": total_to_clean})

    # Confirm
    console.print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}?{CYAN}]{RESET} {YELLOW}Delete {BRIGHT_CYAN}{len(items_to_clean)}{YELLOW} items ({BRIGHT_MAGENTA}{human_readable(total_to_clean)}{YELLOW})? {BRIGHT_CYAN}[y/N]{RESET}: ", end="", flush=True)

    if input().strip().lower() != "y":
        console.print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}Edge cleanup cancelled.{RESET}")
        logger.info("Edge cleanup cancelled at confirmation")
        return

    # Clean
    console.print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}►{CYAN}]{RESET} {BRIGHT_CYAN}CLEANING EDGE CACHE...{RESET}")

    logger.info("Starting Edge cache cleanup", extra={"item_count": len(items_to_clean), "total_size": total_to_clean})

    knight_rider_animation("Purging Edge cache...", colors=colors[:5])

    freed_bytes = 0
    errors = 0

    for path, size, item_type in items_to_clean:
        try:
            logger.debug("Deleting Edge cache item", extra={"path": path, "size": size, "type": item_type})

            if item_type == "dir" and os.path.isdir(path):
                import shutil
                shutil.rmtree(path, ignore_errors=True)
            elif item_type == "file" and os.path.isfile(path):
                os.remove(path)
            freed_bytes += size

        except (OSError, PermissionError) as e:
            errors += 1
            logger.warning("Failed to delete Edge cache item", extra={"path": path, "error": str(e)})

    # Clear animation
    sys.stdout.write("\r" + " " * 100 + "\r")
    sys.stdout.flush()

    # Results
    console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}✓{CYAN}]{RESET} {BRIGHT_CYAN}EDGE CACHE CLEANED{RESET}")
    console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Space reclaimed:{RESET} {BRIGHT_MAGENTA}{human_readable(freed_bytes)}{RESET}")
    console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Items cleaned:{RESET} {BRIGHT_CYAN}{len(items_to_clean) - errors}{RESET}")

    if errors > 0:
        console.print(f"{BOLD}{CYAN}[{RED}!{CYAN}]{RESET} {RED}Failed to clean {errors} items{RESET}")

    console.print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}■{CYAN}]{RESET} {GREEN}Edge cleanup completed!{RESET}")

    logger.info("Edge cache cleanup completed", extra={
        "freed_bytes": freed_bytes,
        "items_cleaned": len(items_to_clean) - errors,
        "errors": errors
    })