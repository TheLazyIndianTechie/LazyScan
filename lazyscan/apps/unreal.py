#!/usr/bin/env python3
"""
Unreal Engine project discovery and cache management for LazyScan.
"""

import sys
import threading

from helpers.secure_operations import secure_delete
from helpers.unreal_cache_helpers import generate_unreal_project_report

from ..apps.unity import prompt_unity_project_selection  # Reuse project selection logic
from ..core.formatting import get_terminal_colors, human_readable
from ..core.logging_config import get_logger
from ..core.ui import get_console, get_random_funny_message, knight_rider_animation

logger = get_logger(__name__)
console = get_console()


def handle_unreal_discovery(args) -> None:
    """Handle the discovery and processing of Unreal projects."""
    from helpers.unreal_launcher import get_unreal_projects

    # Define colors for styled output
    colors = get_terminal_colors()
    (
        CYAN,
        MAGENTA,
        YELLOW,
        RESET,
        BOLD,
        BRIGHT_CYAN,
        BRIGHT_MAGENTA,
        GREEN,
        RED,
    ) = colors[:9]

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

        # Display individual cache directories
        console.print(f"\n{CYAN}Cache Directories:{RESET}")
        for cache_name, cache_info in report["cache_dirs"].items():
            if cache_info["exists"]:
                console.print(
                    f"  {GREEN}✓{RESET} {cache_name}: {BRIGHT_MAGENTA}{human_readable(cache_info['size'])}{RESET}"
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
                console.print("  i - Intermediate")
                console.print("  s - Saved/Logs")
                console.print("  c - Saved/Crashes")
                console.print("  d - DerivedDataCache")
                console.print("  b - Binaries")
                console.print("  n - None (skip)")

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
                        "i": "Intermediate",
                        "s": "Saved/Logs",
                        "c": "Saved/Crashes",
                        "d": "DerivedDataCache",
                        "b": "Binaries",
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

                        # Use secure deletion for safe removal with backups and audit trails
                        result = secure_delete(
                            [cache_info["path"]], f"Unreal Cache Cleanup - {cache_name}"
                        )

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
                                result.error or "Unknown error during secure deletion"
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
                            f"  {RED}✗ Failed to clear {cache_name}:{RESET} {e!s}"
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
