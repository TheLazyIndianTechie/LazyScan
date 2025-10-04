#!/usr/bin/env python3
"""
VSCode integration module for LazyScan.
Discovers VSCode installations, analyzes cache sizes, and provides safe cleanup options.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional, Callable

from ..core.logging_config import get_logger, get_console
from ..core.formatting import human_readable, get_terminal_colors
from ..core.ui import show_disclaimer
from ..core.scanner import scan_directory_with_progress, get_disk_usage
from ..security.safe_delete import get_safe_deleter, DeletionMode
from ..platforms.macos import VSCODE_PATHS as MACOS_VSCODE_PATHS
from ..platforms.windows import VSCODE_PATHS as WINDOWS_VSCODE_PATHS
from ..platforms.linux import VSCODE_PATHS as LINUX_VSCODE_PATHS

logger = get_logger(__name__)
console = get_console()


class VSCodePlugin:
    """Plugin for VSCode cache analysis and management."""

    @property
    def name(self) -> str:
        return "vscode"

    @property
    def description(self) -> str:
        return "VSCode cache analysis and management"

    def scan(self, **kwargs) -> Dict[str, Any]:
        """Perform VSCode-specific scanning."""
        try:
            # Get VSCode cache paths
            cache_paths = get_platform_vscode_paths()

            total_size = 0
            cache_items = []

            # Scan each cache path
            for cache_path in cache_paths:
                if cache_path.exists():
                    try:
                        # Calculate size of cache directory
                        size = get_disk_usage(str(cache_path))
                        if size > 0:
                            cache_items.append({
                                "path": str(cache_path),
                                "size": size,
                                "type": "directory"
                            })
                            total_size += size
                    except (OSError, PermissionError):
                        continue

            if not cache_items:
                return {
                    "status": "no_cache",
                    "message": "No VSCode cache found",
                    "cache_items": [],
                    "total_size": 0
                }

            return {
                "status": "success",
                "cache_items": cache_items,
                "total_size": total_size,
                "item_count": len(cache_items)
            }

        except Exception as e:
            logger.error(f"VSCode scan failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "total_size": 0
            }

    def clean(self, **kwargs) -> Dict[str, Any]:
        """Perform VSCode-specific cleaning."""
        try:
            from helpers.secure_operations import secure_delete
            from ..core.ui import knight_rider_animation, get_console
            from ..core.formatting import get_terminal_colors, human_readable

            console = get_console()
            colors = get_terminal_colors()
            CYAN, MAGENTA, YELLOW, RESET, BOLD, BRIGHT_CYAN, BRIGHT_MAGENTA, GREEN, RED = colors[:9]

            # Get VSCode cache paths
            cache_paths = get_platform_vscode_paths()

            # Collect cache directories to clean
            paths_to_clean = []
            total_size = 0

            for cache_path in cache_paths:
                if cache_path.exists():
                    try:
                        size = get_disk_usage(str(cache_path))
                        if size > 0:
                            paths_to_clean.append(str(cache_path))
                            total_size += size
                    except (OSError, PermissionError):
                        continue

            if not paths_to_clean:
                return {
                    "status": "success",
                    "message": "No VSCode cache directories to clean",
                    "cleaned_items": 0,
                    "total_size": 0
                }

            # Show cleaning animation
            console.print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}VSCODE CLEAN{CYAN}]{RESET} {YELLOW}Cleaning VSCode cache...{RESET}")
            knight_rider_animation("Purging VSCode cache...", colors=colors[:5])

            # Use secure deletion
            result = secure_delete(paths_to_clean, "VSCode Cache Cleanup")

            # Clear animation
            import sys
            sys.stdout.write("\r" + " " * 100 + "\r")
            sys.stdout.flush()

            if result.success:
                console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}✓{CYAN}]{RESET} {BRIGHT_CYAN}VSCODE CACHE CLEANED{RESET}")
                console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Space reclaimed:{RESET} {BRIGHT_MAGENTA}{human_readable(result.size_processed)}{RESET}")
                console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Items cleaned:{RESET} {BRIGHT_CYAN}{result.files_processed}{RESET}")

                if result.errors:
                    console.print(f"{BOLD}{CYAN}[{RED}!{CYAN}]{RESET} {RED}Failed to clean {len(result.errors)} items{RESET}")

                return {
                    "status": "success",
                    "message": "VSCode cache cleaned successfully",
                    "cleaned_items": result.files_processed,
                    "total_size": result.size_processed,
                    "errors": result.errors
                }
            else:
                return {
                    "status": "error",
                    "message": f"VSCode cleaning failed: {result.message}",
                    "cleaned_items": result.files_processed,
                    "total_size": result.size_processed,
                    "errors": result.errors
                }

        except Exception as e:
            logger.error(f"VSCode clean failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "cleaned_items": 0,
                "total_size": 0
            }


def get_platform_vscode_paths() -> List[Path]:
    """
    Get VSCode cache paths for the current platform.

    Returns:
        List[Path]: Platform-specific VSCode cache directories.
    """
    import platform

    system = platform.system().lower()

    if system == "darwin":
        return [Path(p) for p in MACOS_VSCODE_PATHS if p]
    elif system == "windows":
        return [Path(p) for p in WINDOWS_VSCODE_PATHS if p]
    elif system == "linux":
        return [Path(p) for p in LINUX_VSCODE_PATHS if p]
    else:
        logger.warning(
            f"Unsupported platform: {system}. Falling back to generic paths."
        )
        return [
            Path.home() / ".vscode" / "extensions",
            Path.home() / ".config" / "Code" / "Cache",
            Path.home() / ".cache" / "Code",
        ]


def discover_vscode_profiles(base_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    Discover VSCode user profiles and their cache directories.

    Args:
        base_dir: Optional base directory to search (defaults to platform paths).

    Returns:
        List[Dict]: List of discovered profiles with paths and metadata.
    """
    profiles = []
    search_paths = get_platform_vscode_paths()

    if base_dir:
        search_paths = [base_dir]

    for root_path in search_paths:
        if not root_path.exists():
            continue

        logger.debug(f"Searching VSCode paths in: {root_path}")

        # Common VSCode cache subdirs
        cache_dirs = [
            "Cache",
            "CachedData",
            "Code Cache",
            "logs",
            "extensions",
            "User",
        ]

        for cache_dir in cache_dirs:
            full_path = root_path / cache_dir
            if full_path.exists():
                size_mb = get_disk_usage(str(full_path)) / (1024 * 1024)
                profiles.append(
                    {
                        "name": f"VSCode {cache_dir}",
                        "path": full_path,
                        "size_mb": size_mb,
                        "type": (
                            "cache"
                            if "Cache" in cache_dir or "Code Cache" in cache_dir
                            else "logs/extensions"
                        ),
                    }
                )
                logger.info(
                    f"Discovered VSCode {cache_dir}: {full_path} ({human_readable(size_mb * 1024 * 1024)})"
                )

    return profiles


def scan_vscode_caches(profiles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Scan VSCode caches for detailed size analysis.

    Args:
        profiles: List of VSCode profiles from discover_vscode_profiles.

    Returns:
        Dict: Aggregated scan results with total sizes and top items.
    """
    results = {
        "total_size_mb": 0,
        "profiles": [],
        "top_items": [],
    }

    for profile in profiles:
        path = profile["path"]
        console.print_info(f"Scanning {profile['name']}: {path}")

        # Scan with progress
        colors = get_terminal_colors()
        items = list(scan_directory_with_progress(str(path), colors))

        profile_size_mb = sum(item[1] for item in items) / (1024 * 1024)
        results["total_size_mb"] += profile_size_mb

        profile_results = {
            "name": profile["name"],
            "path": path,
            "size_mb": profile_size_mb,
            "items": items[:10],  # Top 10 items per profile
        }
        results["profiles"].append(profile_results)

        # Collect top items across all
        results["top_items"].extend(items)

    # Sort top items by size
    results["top_items"].sort(key=lambda x: x["size"], reverse=True)
    results["top_items"] = results["top_items"][:20]  # Global top 20

    logger.info(
        f"VSCode scan complete. Total size: {human_readable(results['total_size_mb'] * 1024 * 1024)}"
    )
    return results


def cleanup_vscode_cache(
    profiles: List[Dict[str, Any]],
    dry_run: bool = True,
    force: bool = False,
) -> bool:
    """
    Safely clean VSCode caches.

    Args:
        profiles: Profiles to clean.
        dry_run: If True, simulate cleanup.
        force: If True, skip confirmations.

    Returns:
        bool: True if cleanup successful.
    """
    deleter = get_safe_deleter()
    total_freed_mb = 0

    for profile in profiles:
        path = profile["path"]
        console.print_warning(
            f"Preparing to clean: {profile['name']} ({human_readable(profile['size_mb'] * 1024 * 1024)})"
        )

        if not dry_run:
            if not force:
                response = input(f"Delete {profile['name']}? (y/N): ").strip().lower() == "y"
                if not response:
                    logger.info(f"Cleanup skipped for {path} by user")
                    continue

            try:
                success = deleter.delete(
                    path,
                    mode=DeletionMode.TRASH,
                    dry_run=False,
                    force=force,
                    context="vscode_cache_cleanup",
                )
                if success:
                    total_freed_mb += profile["size_mb"]
                    console.print_success(f"Cleaned {profile['name']}")
                else:
                    console.print_error(f"Failed to clean {profile['name']}")
            except Exception as e:
                logger.error(f"Error cleaning {path}: {e}")
                console.print_error(f"Error: {e}")
                return False
        else:
            console.print_info(f"DRY RUN: Would clean {path}")
            total_freed_mb += profile["size_mb"]

    if dry_run:
        console.print_info(
            f"DRY RUN COMPLETE. Would free: {human_readable(total_freed_mb * 1024 * 1024)}"
        )
    else:
        console.print_success(
            f"Cleanup complete. Freed: {human_readable(total_freed_mb * 1024 * 1024)}"
        )

    return True


def handle_vscode_discovery(args: Any) -> int:
    """
    Main handler for VSCode discovery and cleanup via CLI.

    Args:
        args: CLI arguments (e.g., dry_run, force).

    Returns:
        int: Exit code (0 for success).
    """
    show_disclaimer()

    console.print("🔧 VSCode Cache Analysis")

    # Discover profiles
    profiles = discover_vscode_profiles()
    if not profiles:
        console.print_warning("No VSCode profiles or caches found.")
        logger.warning("No VSCode paths discovered")
        return 1

    # Display summary
    total_size = sum(p["size_mb"] for p in profiles)
    console.print(
        f"\nFound {len(profiles)} VSCode cache(s) totaling {human_readable(total_size * 1024 * 1024)}"
    )

    # Table of profiles
    table_data = []
    for p in profiles:
        table_data.append(
            [
                p["name"],
                human_readable(p["size_mb"] * 1024 * 1024),
                p["type"],
                str(p["path"]),
            ]
        )

    # Display profile table
    console.print("\nProfile | Size | Type | Path")
    console.print("-" * 50)
    for row in table_data:
        console.print(f"{row[0]} | {row[1]} | {row[2]} | {row[3]}")

    # Scan for details if not dry-run only
    if not args.dry_run:
        results = scan_vscode_caches(profiles)

        # Show top items
        console.print("📊 Top VSCode Cache Items")
        top_table = []
        for item in results["top_items"]:
            top_table.append(
                [
                    human_readable(item["size"]),
                    (
                        item["name"][:40] + "..."
                        if len(item["name"]) > 40
                        else item["name"]
                    ),
                    str(item["path"]),
                ]
            )

        # Display top items table
        console.print("\nSize | Item | Path")
        console.print("-" * 50)
        for row in top_table:
            console.print(f"{row[0]} | {row[1]} | {row[2]}")

    # Cleanup if requested
    if args.clean:
        success = cleanup_vscode_cache(profiles, dry_run=args.dry_run, force=args.force)
        if not success:
            return 1

    return 0


def get_vscode_handler() -> Callable:
    """Get the main VSCode handler for CLI integration."""
    return handle_vscode_discovery
