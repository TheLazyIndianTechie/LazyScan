#!/usr/bin/env python3
"""
Unreal Engine project discovery and cache management for LazyScan.
"""

import sys
import threading
import asyncio
from typing import Dict, Any

from ..core.logging_config import get_logger
from ..core.formatting import human_readable, get_terminal_colors
from ..core.ui import knight_rider_animation, get_random_funny_message, get_console
from ..apps.unity import prompt_unity_project_selection  # Reuse project selection logic
from helpers.unreal_cache_helpers import generate_unreal_project_report
from helpers.secure_operations import secure_delete


logger = get_logger(__name__)
console = get_console()


class UnrealPlugin:
    """Plugin for Unreal Engine project discovery and cache management."""

    @property
    def name(self) -> str:
        return "unreal"

    @property
    def description(self) -> str:
        return "Unreal Engine project discovery and cache management"

    def scan(self, **kwargs) -> Dict[str, Any]:
        """Perform Unreal-specific scanning."""
        try:
            # TODO: Implement Unreal project scanning
            return {
                "status": "not_implemented",
                "message": "Unreal scanning not yet implemented in plugin interface",
                "projects": [],
                "total_size": 0
            }
        except Exception as e:
            logger.error(f"Unreal scan failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "projects": [],
                "total_size": 0
            }

    def clean(self, **kwargs) -> Dict[str, Any]:
        """Perform Unreal-specific cleaning."""
        try:
            from helpers.secure_operations import secure_delete
            from helpers.unreal_launcher import get_unreal_projects
            from helpers.unreal_cache_helpers import generate_unreal_project_report
            from ..core.ui import knight_rider_animation, get_console
            from ..core.formatting import get_terminal_colors, human_readable

            console = get_console()
            colors = get_terminal_colors()
            CYAN, MAGENTA, YELLOW, RESET, BOLD, BRIGHT_CYAN, BRIGHT_MAGENTA, GREEN, RED = colors[:9]

            # Get Unreal projects
            projects = get_unreal_projects()
            if not projects:
                return {
                    "status": "error",
                    "message": "No Unreal projects found",
                    "cleaned_items": 0,
                    "total_size": 0
                }

            # For plugin interface, clean cache directories from all projects
            paths_to_clean = []
            total_size = 0

            for project_path in projects:
                try:
                    report = generate_unreal_project_report(project_path)
                    # Assuming report has cache_dirs similar to Unity
                    if "cache_dirs" in report:
                        for cache_name, cache_info in report["cache_dirs"].items():
                            if cache_info.get("exists", False):
                                paths_to_clean.append(cache_info["path"])
                                total_size += cache_info.get("size", 0)
                except Exception as e:
                    logger.warning(f"Failed to analyze Unreal project {project_path}: {e}")
                    continue

            if not paths_to_clean:
                return {
                    "status": "success",
                    "message": "No Unreal cache directories to clean",
                    "cleaned_items": 0,
                    "total_size": 0
                }

            # Show cleaning animation
            console.print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}UNREAL CLEAN{CYAN}]{RESET} {YELLOW}Cleaning Unreal cache...{RESET}")
            knight_rider_animation("Purging Unreal cache...", colors=colors[:5])

            # Use secure deletion with Unreal context for policy enforcement
            result = secure_delete(paths_to_clean, "Unreal Cache Cleanup", "unreal")

            # Clear animation
            import sys
            sys.stdout.write("\r" + " " * 100 + "\r")
            sys.stdout.flush()

            if result.success:
                console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}✓{CYAN}]{RESET} {BRIGHT_CYAN}UNREAL CACHE CLEANED{RESET}")
                console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Space reclaimed:{RESET} {BRIGHT_MAGENTA}{human_readable(result.size_processed)}{RESET}")
                console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Items cleaned:{RESET} {BRIGHT_CYAN}{result.files_processed}{RESET}")

                if result.errors:
                    console.print(f"{BOLD}{CYAN}[{RED}!{CYAN}]{RESET} {RED}Failed to clean {len(result.errors)} items{RESET}")

                return {
                    "status": "success",
                    "message": "Unreal cache cleaned successfully",
                    "cleaned_items": result.files_processed,
                    "total_size": result.size_processed,
                    "errors": result.errors
                }
            else:
                return {
                    "status": "error",
                    "message": f"Unreal cleaning failed: {result.message}",
                    "cleaned_items": result.files_processed,
                    "total_size": result.size_processed,
                    "errors": result.errors
                }

        except Exception as e:
            logger.error(f"Unreal clean failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "cleaned_items": 0,
                "total_size": 0
            }

    async def scan_async(self, **kwargs) -> Dict[str, Any]:
        """Perform Unreal-specific scanning asynchronously."""
        # Delegate to sync implementation since Unreal scanning is I/O bound
        return await asyncio.get_event_loop().run_in_executor(None, self.scan, **kwargs)

    async def clean_async(self, **kwargs) -> Dict[str, Any]:
        """Perform Unreal-specific cleaning asynchronously."""
        # Delegate to sync implementation since Unreal cleaning involves filesystem operations
        return await asyncio.get_event_loop().run_in_executor(None, self.clean, **kwargs)


def handle_unreal_discovery(args) -> None:
    """Handle the discovery and processing of Unreal projects."""
    from helpers.unreal_launcher import get_unreal_projects

    # Define colors for styled output
    colors = get_terminal_colors()
    CYAN, MAGENTA, YELLOW, RESET, BOLD, BRIGHT_CYAN, BRIGHT_MAGENTA, GREEN, RED = (
        colors[:9]
    )

    logger.info(
        "Starting Unreal Engine project discovery",
        extra={"operation": "unreal_discovery"},
    )

    # Discover Unreal projects using the launcher and custom paths
    console.print(
        f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}UNREAL ENGINE SCANNER{CYAN}]{RESET} {YELLOW}Searching for Unreal Engine projects...{RESET}"
    )

    # Select a random funny message
    funny_msg = get_random_funny_message()

    # Show animation while discovering projects
    projects = []
    discovery_done = False

    def discover_projects():
        nonlocal projects, discovery_done
        try:
            projects = get_unreal_projects()
            logger.info(
                "Unreal project discovery completed",
                extra={"project_count": len(projects)},
            )
        except Exception as e:
            logger.error("Unreal project discovery failed", extra={"error": str(e)})
            projects = []
        discovery_done = True

    # Run discovery in a thread
    discovery_thread = threading.Thread(target=discover_projects)
    discovery_thread.start()

    # Show animation while discovering
    while discovery_thread.is_alive():
        knight_rider_animation(funny_msg, iterations=1, colors=colors[:5])
        if not discovery_thread.is_alive():
            break

    discovery_thread.join()

    if not projects:
        console.print(
            f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}No Unreal Engine projects found.{RESET}"
        )
        logger.warning("No Unreal Engine projects found")
        return

    console.print(
        f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}✓{CYAN}]{RESET} {GREEN}Found {len(projects)} Unreal Engine projects.{RESET}"
    )

    # Prompt user to select projects
    if sys.stdin.isatty():
        selected_projects = prompt_unity_project_selection(
            projects
        )  # Reuse Unity selection logic
    else:
        console.print("Non-interactive terminal. Using all projects.")
        logger.info("Non-interactive mode, using all projects")
        selected_projects = projects

    if not selected_projects:
        console.print(
            f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}No Unreal projects selected.{RESET}"
        )
        logger.warning("No Unreal projects selected")
        return

    console.print(
        f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}UNREAL SCANNER{CYAN}]{RESET} {YELLOW}Generating Unreal Project Reports...{RESET}"
    )
    logger.info(
        "Starting Unreal project report generation",
        extra={"selected_count": len(selected_projects)},
    )

    total_size = 0
    total_freed = 0

    for project in selected_projects:
        logger.debug(
            "Processing Unreal project",
            extra={
                "project_name": project.get("name", "Unknown"),
                "project_path": project["path"],
            },
        )

        report = generate_unreal_project_report(project["path"])
        total_size += report["total_size"]

        # Display the report
        console.print(
            f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}PROJECT{CYAN}]{RESET} {YELLOW}{report['name']}{RESET}"
        )
        console.print(f"{CYAN}Path:{RESET} {GREEN}{report['path']}{RESET}")
        console.print(
            f"{CYAN}Total Cache Size:{RESET} {BRIGHT_MAGENTA}{human_readable(report['total_size'])}{RESET}"
        )

        # Display engine version if available
        if report.get("engine_version"):
            console.print(f"{CYAN}Engine Version:{RESET} {BRIGHT_MAGENTA}{report['engine_version']}{RESET}")

        # Display individual cache directories with warnings
        console.print(f"\n{CYAN}Cache Directories:{RESET}")
        for cache_name, cache_info in report["cache_dirs"].items():
            if cache_info["exists"]:
                size_str = f"{BRIGHT_MAGENTA}{human_readable(cache_info['size'])}{RESET}"
                warning_indicator = ""
                if cache_info.get("warn_on_delete", False):
                    warning_indicator = f"{RED}⚠{RESET} "
                elif cache_info.get("requires_backup", False):
                    warning_indicator = f"{YELLOW}⚡{RESET} "

                description = cache_info.get("description", "")
                if description:
                    console.print(
                        f"  {warning_indicator}{GREEN}✓{RESET} {cache_name}: {size_str} - {description}"
                    )
                else:
                    console.print(
                        f"  {warning_indicator}{GREEN}✓{RESET} {cache_name}: {size_str}"
                    )
            else:
                console.print(
                    f"  {YELLOW}✗{RESET} {cache_name}: {YELLOW}Not found{RESET}"
                )

        # Ask if the user wants to clean caches if in interactive mode and caches exist
        if sys.stdin.isatty() and report["total_size"] > 0:
            console.print(
                f"\n{CYAN}Would you like to clean cache directories for this project?{RESET}"
            )
            response = input("Clean caches? (y/N): ").strip().lower()

            if response == "y":
                logger.info(
                    "User chose to clean Unreal project caches",
                    extra={
                        "project_name": report["name"],
                        "project_path": report["path"],
                    },
                )

                # Options for clearing specific cache types
                console.print("\nChoose which cache directories to clear:")
                console.print("  a - All")
                console.print("  b - Binaries")
                console.print("  c - Saved/Crashes")
                console.print("  d - DerivedDataCache")
                console.print("  i - Intermediate")
                console.print("  l - Saved/Logs")
                console.print("  p - Plugins/Intermediate")
                console.print("  q - Plugins/Binaries")
                console.print("  m - MarketplaceAssets")
                console.print("  e - LauncherCache")
                console.print("  n - None (skip)")

                # Show warnings for rebuild-required caches
                rebuild_caches = [name for name, info in report["cache_dirs"].items()
                                if info.get("warn_on_delete", False) and info["exists"]]
                if rebuild_caches:
                    console.print(f"\n{RED}⚠ Warning: The following caches require rebuild after deletion:{RESET}")
                    for cache_name in rebuild_caches:
                        cache_info = report["cache_dirs"][cache_name]
                        console.print(f"  {RED}•{RESET} {cache_name}: {cache_info.get('description', '')}")

                backup_caches = [name for name, info in report["cache_dirs"].items()
                               if info.get("requires_backup", False) and info["exists"]]
                if backup_caches:
                    console.print(f"\n{YELLOW}⚡ Recommendation: Backup these caches before deletion:{RESET}")
                    for cache_name in backup_caches:
                        cache_info = report["cache_dirs"][cache_name]
                        console.print(f"  {YELLOW}•{RESET} {cache_name}: {cache_info.get('description', '')}")

                choices = (
                    input("Enter choices separated by commas (e.g., i,s,c): ")
                    .strip()
                    .lower()
                    .split(",")
                )

                logger.info(
                    "User selected Unreal cache cleanup options",
                    extra={"project_name": report["name"], "choices": choices},
                )

                # Skip if 'n' is selected
                if "n" in choices:
                    console.print(
                        f"{YELLOW}Skipping cache cleaning for this project.{RESET}"
                    )
                    logger.info(
                        "User skipped cache cleaning for project",
                        extra={"project_name": report["name"]},
                    )
                    continue

                # Determine directories to clear
                directories_to_clear = []
                if "a" in choices:
                    directories_to_clear = [
                        name
                        for name, info in report["cache_dirs"].items()
                        if info["exists"]
                    ]
                else:
                    available_choices = {
                        "b": "Binaries",
                        "c": "Saved/Crashes",
                        "d": "DerivedDataCache",
                        "i": "Intermediate",
                        "l": "Saved/Logs",
                        "p": "Plugins/Intermediate",
                        "q": "Plugins/Binaries",
                        "m": "MarketplaceAssets",
                        "e": "LauncherCache",
                    }
                    for choice in choices:
                        if (
                            choice in available_choices
                            and available_choices[choice] in report["cache_dirs"]
                        ):
                            if report["cache_dirs"][available_choices[choice]][
                                "exists"
                            ]:
                                directories_to_clear.append(available_choices[choice])

                # Clean selected directories
                project_freed = 0
                for cache_name in directories_to_clear:
                    cache_info = report["cache_dirs"][cache_name]
                    try:
                        size_before = cache_info["size"]

                        logger.info(
                            "Starting Unreal cache deletion",
                            extra={
                                "project_name": report["name"],
                                "cache_name": cache_name,
                                "cache_path": cache_info["path"],
                                "cache_size": size_before,
                            },
                        )

                        # Handle selective backups for flagged caches
                        paths_to_delete = [cache_info["path"]]
                        backup_created = False

                        if cache_info.get("requires_backup", False):
                            try:
                                from helpers.security import create_backup
                                import uuid
                                operation_id = str(uuid.uuid4())[:8]

                                console.print(f"  {YELLOW}⚡ Creating backup for {cache_name}...{RESET}")
                                backup_path = create_backup(cache_info["path"], operation_id)
                                if backup_path:
                                    console.print(f"  {GREEN}✓ Backup created: {backup_path}{RESET}")
                                    backup_created = True
                                    logger.info(
                                        "Backup created for flagged cache",
                                        extra={
                                            "project_name": report["name"],
                                            "cache_name": cache_name,
                                            "backup_path": backup_path,
                                        },
                                    )
                                else:
                                    console.print(f"  {RED}✗ Backup creation failed for {cache_name}{RESET}")
                                    logger.warning(
                                        "Backup creation failed for flagged cache",
                                        extra={
                                            "project_name": report["name"],
                                            "cache_name": cache_name,
                                        },
                                    )
                            except Exception as e:
                                console.print(f"  {RED}✗ Backup error for {cache_name}: {str(e)}{RESET}")
                                logger.error(
                                    "Backup creation exception",
                                    extra={
                                        "project_name": report["name"],
                                        "cache_name": cache_name,
                                        "error": str(e),
                                    },
                                    exc_info=True,
                                )

                        # Use secure deletion for safe removal with backups and audit trails
                        # Disable automatic backups since we handle them selectively above
                        from helpers.secure_operations import configure_security
                        original_backup_setting = None

                        if cache_info.get("requires_backup", False):
                            # Temporarily disable automatic backups for caches that require selective backup
                            configure_security(enable_backups=False)
                            original_backup_setting = True

                        result = secure_delete(
                            paths_to_delete, f"Unreal Cache Cleanup - {cache_name}", "unreal"
                        )

                        # Restore original backup setting
                        if original_backup_setting:
                            configure_security(enable_backups=True)

                        if result.success:
                            project_freed += size_before
                            console.print(
                                f"  {GREEN}✓ Cleared:{RESET} {cache_name} ({BRIGHT_MAGENTA}{human_readable(size_before)}{RESET} freed)"
                            )
                            logger.info(
                                "Unreal cache deletion successful",
                                extra={
                                    "project_name": report["name"],
                                    "cache_name": cache_name,
                                    "size_freed": size_before,
                                },
                            )
                        else:
                            error_msg = (
                                result.errors[0] if result.errors else "Unknown error during secure deletion"
                            )
                            if "permission" in error_msg.lower():
                                console.print(
                                    f"  {RED}✗ Permission denied:{RESET} {cache_name}"
                                )
                            elif "not found" in error_msg.lower():
                                console.print(
                                    f"  {YELLOW}✗ Already deleted:{RESET} {cache_name}"
                                )
                            else:
                                console.print(
                                    f"  {RED}✗ Failed to clear {cache_name}:{RESET} {error_msg}"
                                )
                            logger.error(
                                "Unreal cache deletion failed",
                                extra={
                                    "project_name": report["name"],
                                    "cache_name": cache_name,
                                    "error": error_msg,
                                },
                            )
                    except Exception as e:
                        console.print(
                            f"  {RED}✗ Failed to clear {cache_name}:{RESET} {str(e)}"
                        )
                        logger.error(
                            "Unreal cache deletion exception",
                            extra={
                                "project_name": report["name"],
                                "cache_name": cache_name,
                                "error": str(e),
                            },
                            exc_info=True,
                        )

                if project_freed > 0:
                    total_freed += project_freed
                    console.print(
                        f"\n{GREEN}Space freed for this project:{RESET} {BRIGHT_MAGENTA}{human_readable(project_freed)}{RESET}"
                    )
                    logger.info(
                        "Unreal project cleanup completed",
                        extra={
                            "project_name": report["name"],
                            "space_freed": project_freed,
                        },
                    )

    console.print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}SUMMARY{CYAN}]{RESET}")
    console.print(
        f"{CYAN}Total Cache Size for all selected projects:{RESET} {BRIGHT_MAGENTA}{human_readable(total_size)}{RESET}"
    )
    if total_freed > 0:
        console.print(
            f"{GREEN}Total Space Freed:{RESET} {BRIGHT_MAGENTA}{human_readable(total_freed)}{RESET}"
        )

    logger.info(
        "Unreal Engine discovery and cleanup completed",
        extra={
            "total_cache_size": total_size,
            "total_freed": total_freed,
            "projects_processed": len(selected_projects),
        },
    )
