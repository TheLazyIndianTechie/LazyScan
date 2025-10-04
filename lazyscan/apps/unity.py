#!/usr/bin/env python3
"""
Unity Engine project discovery and cache management for LazyScan.
"""

import sys
import threading
from typing import List, Dict, Any
import asyncio

from ..core.logging_config import get_logger
from ..core.formatting import human_readable, get_terminal_colors
from ..core.ui import knight_rider_animation, get_random_funny_message, get_console
from helpers.unity_cache_helpers import generate_unity_project_report
from helpers.unity_hub import read_unity_hub_projects
from helpers.secure_operations import secure_delete


logger = get_logger(__name__)
console = get_console()


def _get_cache_impact_description(cache_name: str, size: int) -> str:
    """Get a human-readable description of cache cleanup impact."""
    size_mb = size / (1024 * 1024)

    if cache_name == "Library":
        if size_mb > 5000:  # > 5GB
            return "Very high - full rebuild required"
        elif size_mb > 1000:  # > 1GB
            return "High - significant rebuild time"
        else:
            return "Medium - moderate rebuild time"
    elif cache_name == "Build":
        if size_mb > 10000:  # > 10GB
            return "Very high - long build time"
        elif size_mb > 2000:  # > 2GB
            return "High - substantial build time"
        else:
            return "Medium - reasonable build time"
    elif cache_name in ["Temp", "obj"]:
        return "Low - quick regeneration"
    elif cache_name == "Logs":
        return "None - safe to clean"
    elif "package" in cache_name.lower():
        return "Medium - download required"
    elif "cache" in cache_name.lower():
        return "Low - auto-regeneration"
    else:
        return "Unknown impact"


class UnityPlugin:
    """Plugin for Unity Engine project discovery and cache management."""

    @property
    def name(self) -> str:
        return "unity"

    @property
    def description(self) -> str:
        return "Unity Engine project discovery and cache management"

    def scan(self, **kwargs) -> Dict[str, Any]:
        """Perform Unity-specific scanning."""
        try:
            from helpers.unity_hub import read_unity_hub_projects
            from helpers.unity_cache_helpers import generate_unity_project_report

            # Read Unity Hub projects
            json_path = kwargs.get('unityhub_json')
            projects = read_unity_hub_projects(json_path) if json_path else read_unity_hub_projects()

            if not projects:
                return {
                    "status": "no_projects",
                    "message": "No Unity projects found",
                    "projects": [],
                    "total_size": 0
                }

            # Generate report for all projects
            report = generate_unity_project_report(projects)

            # Calculate total size safely
            total_size = 0
            for p in projects:
                size = p.get("total_size", 0)
                if isinstance(size, (int, float)):
                    total_size += int(size)

            return {
                "status": "success",
                "projects": projects,
                "report": report,
                "total_size": total_size
            }

        except Exception as e:
            logger.error(f"Unity scan failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "projects": [],
                "total_size": 0
            }

    def clean(self, **kwargs) -> Dict[str, Any]:
        """Perform Unity-specific cleaning."""
        try:
            from helpers.secure_operations import secure_delete
            from helpers.unity_hub import read_unity_hub_projects
            from helpers.unity_cache_helpers import generate_unity_project_report
            from ..core.ui import knight_rider_animation, get_console
            from ..core.formatting import get_terminal_colors, human_readable

            console = get_console()
            colors = get_terminal_colors()
            CYAN, MAGENTA, YELLOW, RESET, BOLD, BRIGHT_CYAN, BRIGHT_MAGENTA, GREEN, RED = colors[:9]

            # Get Unity projects
            json_path = kwargs.get('unityhub_json')
            if json_path:
                projects = read_unity_hub_projects(json_path)
            else:
                projects = read_unity_hub_projects()
            if not projects:
                return {
                    "status": "error",
                    "message": "No Unity projects found",
                    "cleaned_items": 0,
                    "total_size": 0
                }

            # For plugin interface, clean all cache directories from all projects
            paths_to_clean = []
            total_size = 0

            for project in projects:
                # Check config for global cache inclusion
                from ..core.config import get_typed_config
                config = get_typed_config()
                include_global = getattr(config.unity, 'include_global_cache', True)

                report = generate_unity_project_report(
                    project["path"], project["name"],
                    include_global_cache=include_global
                )
                for cache_name, cache_info in report["cache_dirs"].items():
                    if cache_info["exists"]:
                        paths_to_clean.append(cache_info["path"])
                        total_size += cache_info["size"]

            if not paths_to_clean:
                return {
                    "status": "success",
                    "message": "No Unity cache directories to clean",
                    "cleaned_items": 0,
                    "total_size": 0
                }

            # Show cleaning animation
            console.print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}UNITY CLEAN{CYAN}]{RESET} {YELLOW}Cleaning Unity cache...{RESET}")
            knight_rider_animation("Purging Unity cache...", colors=colors[:5])

            # Use secure deletion
            result = secure_delete(paths_to_clean, "Unity Cache Cleanup")

            # Clear animation
            import sys
            sys.stdout.write("\r" + " " * 100 + "\r")
            sys.stdout.flush()

            if result.success:
                console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}✓{CYAN}]{RESET} {BRIGHT_CYAN}UNITY CACHE CLEANED{RESET}")
                console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Space reclaimed:{RESET} {BRIGHT_MAGENTA}{human_readable(result.size_processed)}{RESET}")
                console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Items cleaned:{RESET} {BRIGHT_CYAN}{result.files_processed}{RESET}")

                if result.errors:
                    console.print(f"{BOLD}{CYAN}[{RED}!{CYAN}]{RESET} {RED}Failed to clean {len(result.errors)} items{RESET}")

                return {
                    "status": "success",
                    "message": "Unity cache cleaned successfully",
                    "cleaned_items": result.files_processed,
                    "total_size": result.size_processed,
                    "errors": result.errors
                }
            else:
                return {
                    "status": "error",
                    "message": f"Unity cleaning failed: {result.message}",
                    "cleaned_items": result.files_processed,
                    "total_size": result.size_processed,
                    "errors": result.errors
                }

        except Exception as e:
            logger.error(f"Unity clean failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "cleaned_items": 0,
                "total_size": 0
            }

    async def scan_async(self, **kwargs) -> Dict[str, Any]:
        """Perform Unity-specific scanning asynchronously."""
        # For now, delegate to sync implementation since Unity scanning is I/O bound
        # and doesn't benefit significantly from async
        return await asyncio.get_event_loop().run_in_executor(None, self.scan, **kwargs)

    async def clean_async(self, **kwargs) -> Dict[str, Any]:
        """Perform Unity-specific cleaning asynchronously."""
        # For now, delegate to sync implementation since Unity cleaning involves
        # filesystem operations that are already handled asynchronously in secure_delete
        return await asyncio.get_event_loop().run_in_executor(None, self.clean, **kwargs)


def prompt_unity_project_selection(
    projects: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Prompt user to select Unity projects."""
    logger.info(
        "Prompting user for Unity project selection",
        extra={
            "operation": "project_selection",
            "project_count": len(projects),
            "interactive": sys.stdin.isatty(),
        },
    )

    # Check if the terminal is interactive
    if not sys.stdin.isatty():
        logger.warning("Non-interactive terminal detected, skipping project selection")
        console.print("Non-interactive terminal. Skipping project selection.")
        return []

    console.print("\nAvailable Unity Projects:")
    for index, project in enumerate(projects, 1):
        console.print(f"{index}) {project['name']} ({project['path']})")

    console.print("0) All projects")
    console.print("Q) Quit")

    selected_projects = []
    while not selected_projects:
        selection = input(
            "Select projects by number (comma or space-separated): "
        ).strip()
        if selection.strip().lower() == "q":
            logger.info("User quit project selection")
            return []

        try:
            indexes = set(
                int(x) for x in selection.replace(",", " ").split() if x.isdigit()
            )

            if 0 in indexes:
                logger.info("User selected all projects")
                return projects

            selected_projects = [
                projects[i - 1] for i in indexes if 0 < i <= len(projects)
            ]

            if not selected_projects:
                console.print("No valid selections made. Please try again.")
                logger.warning(
                    "No valid project selections made", extra={"input": selection}
                )
        except ValueError as e:
            console.print(
                "Invalid input. Please enter numbers separated by commas or spaces."
            )
            logger.warning(
                "Invalid project selection input",
                extra={"input": selection, "error": str(e)},
            )

    logger.info(
        "User selected Unity projects",
        extra={
            "selected_count": len(selected_projects),
            "selected_projects": [p["name"] for p in selected_projects],
        },
    )

    return selected_projects


def handle_unity_discovery(args) -> None:
    """Handle the discovery and processing of Unity projects."""
    logger.info(
        "Starting Unity project discovery",
        extra={
            "operation": "unity_discovery",
            "no_unityhub": args.no_unityhub,
            "clean_mode": args.clean,
        },
    )

    handle_unity_projects_integration(args)


def handle_unity_projects_integration(args) -> None:
    """Handle the discovery of Unity projects via Unity Hub and existing methodologies."""
    logger.debug(
        "Handling Unity projects integration", extra={"no_unityhub": args.no_unityhub}
    )

    if not args.no_unityhub:
        scan_unity_project_via_hub(args, clean=args.clean)
    else:
        logger.info("Unity Hub disabled, falling back to directory picker")
        from ..core.scanner import default_directory_picker

        default_directory_picker()


def scan_unity_project_via_hub(args, clean: bool = False) -> None:
    """Scan Unity projects via Unity Hub and generate a report."""
    colors = get_terminal_colors()
    CYAN, MAGENTA, YELLOW, RESET, BOLD, BRIGHT_CYAN, BRIGHT_MAGENTA, GREEN, RED = (
        colors[:9]
    )

    logger.info(
        "Starting Unity Hub scanner",
        extra={
            "operation": "unity_hub_scan",
            "clean_mode": clean,
            "unityhub_json": getattr(args, "unityhub_json", None),
        },
    )

    console.print(
        f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}UNITY HUB SCANNER{CYAN}]{RESET} {YELLOW}Discovering Unity projects via Unity Hub...{RESET}"
    )

    # Select a random funny message
    funny_msg = get_random_funny_message()

    # Show animation while discovering projects
    projects = []
    discovery_done = False

    def discover_unity_projects():
        nonlocal projects, discovery_done
        try:
            unity_hub_json_path = args.unityhub_json if args.unityhub_json else None
            projects = read_unity_hub_projects(unity_hub_json_path)  # type: ignore
            logger.info(
                "Unity project discovery completed",
                extra={
                    "project_count": len(projects),
                    "json_path": unity_hub_json_path,
                },
            )
        except Exception as e:
            logger.error(
                "Unity project discovery failed",
                extra={
                    "error": str(e),
                    "json_path": getattr(args, "unityhub_json", None),
                },
            )
            # Store exception to handle after animation
            projects = e
        discovery_done = True

    # Run discovery in a thread
    discovery_thread = threading.Thread(target=discover_unity_projects)
    discovery_thread.start()

    # Show animation while discovering
    while discovery_thread.is_alive():
        knight_rider_animation(funny_msg, iterations=1, colors=colors[:5])
        if not discovery_thread.is_alive():
            break

    discovery_thread.join()

    # Check if an exception occurred
    if isinstance(projects, Exception):
        logger.error(
            "Unity project discovery failed with exception",
            extra={"exception_type": type(projects).__name__, "error": str(projects)},
        )
        raise projects

    try:
        if not projects:
            console.print(
                f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}No Unity projects found in Unity Hub.{RESET}"
            )
            logger.warning("No Unity projects found in Unity Hub")
            return

        console.print(
            f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}✓{CYAN}]{RESET} {GREEN}Found {len(projects)} Unity projects in Unity Hub.{RESET}"
        )

        # Prompt user to select projects if not in clean mode or if there are multiple projects
        selected_projects: list = []
        if clean and not args.pick and len(projects) > 0:
            # If in clean mode and not forcing pick, assume all projects are to be cleaned
            selected_projects = projects
            logger.info("Auto-selecting all projects for cleaning")
        else:
            selected_projects = prompt_unity_project_selection(projects)

        if not selected_projects:
            console.print(
                f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}No Unity projects selected. Aborting scan.{RESET}"
            )
            logger.warning("No Unity projects selected, aborting scan")
            return

        console.print(
            f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}UNITY SCANNER{CYAN}]{RESET} {YELLOW}Generating Unity Project Reports...{RESET}"
        )
        logger.info(
            "Starting Unity project report generation",
            extra={"selected_count": len(selected_projects)},
        )

        for project in selected_projects:
            logger.debug(
                "Processing Unity project",
                extra={
                    "project_name": project["name"],
                    "project_path": project["path"],
                },
            )

            # Check config for global cache inclusion
            from ..core.config import get_typed_config
            config = get_typed_config()
            include_global = getattr(config.unity, 'include_global_cache', True)

            report = generate_unity_project_report(
                project["path"], project["name"],
                include_build=args.build_dir,
                include_global_cache=include_global
            )

            # Display the report
            console.print(
                f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}PROJECT{CYAN}]{RESET} {YELLOW}{report['name']}{RESET}"
            )
            console.print(f"{CYAN}Path:{RESET} {GREEN}{report['path']}{RESET}")

            # Display Unity version if detected
            if report.get('unity_version'):
                console.print(f"{CYAN}Unity Version:{RESET} {BRIGHT_CYAN}{report['unity_version']}{RESET}")

            console.print(
                f"{CYAN}Total Cache Size:{RESET} {BRIGHT_MAGENTA}{human_readable(report['total_size'])}{RESET}"
            )

            # Display individual cache directories with impact assessment
            console.print(f"\n{CYAN}Cache Directories:{RESET}")

            # Group cache directories by type and calculate impact
            project_caches = {}
            global_caches = {}
            total_project_size = 0
            total_global_size = 0

            for cache_name, cache_info in report["cache_dirs"].items():
                if cache_name in ["Library", "Temp", "obj", "Logs", "Build"]:
                    project_caches[cache_name] = cache_info
                    if cache_info["exists"]:
                        total_project_size += cache_info["size"]
                else:
                    global_caches[cache_name] = cache_info
                    if cache_info["exists"]:
                        total_global_size += cache_info["size"]

            # Display project-local caches with impact
            if project_caches:
                console.print(f"  {CYAN}Project Caches:{RESET}")
                for cache_name, cache_info in project_caches.items():
                    if cache_info["exists"]:
                        size_str = human_readable(cache_info['size'])
                        impact = _get_cache_impact_description(cache_name, cache_info['size'])
                        console.print(
                            f"    {GREEN}✓{RESET} {cache_name}: {BRIGHT_MAGENTA}{size_str}{RESET} {YELLOW}({impact}){RESET}"
                        )
                    else:
                        console.print(
                            f"    {YELLOW}✗{RESET} {cache_name}: {YELLOW}Not found{RESET}"
                        )

                if total_project_size > 0:
                    console.print(f"    {CYAN}Total Project Impact: {BRIGHT_MAGENTA}{human_readable(total_project_size)}{RESET}")

            # Display global Unity caches with impact
            if global_caches:
                console.print(f"  {CYAN}Global Unity Caches:{RESET}")
                for cache_name, cache_info in global_caches.items():
                    if cache_info["exists"]:
                        size_str = human_readable(cache_info['size'])
                        impact = _get_cache_impact_description(cache_name, cache_info['size'])
                        console.print(
                            f"    {GREEN}✓{RESET} {cache_name}: {BRIGHT_MAGENTA}{size_str}{RESET} {YELLOW}({impact}){RESET}"
                        )
                    else:
                        console.print(
                            f"    {YELLOW}✗{RESET} {cache_name}: {YELLOW}Not found{RESET}"
                        )

                if total_global_size > 0:
                    console.print(f"    {CYAN}Total Global Impact: {BRIGHT_MAGENTA}{human_readable(total_global_size)}{RESET}")

            console.print()

            # Ask if the user wants to clear cache directories
            # Options for clearing specific cache types
            console.print("Choose which cache directories to clear:")
            console.print("  a - All")
            console.print("  p - Project caches (Library, Temp, obj, Logs)")
            console.print("  l - Library")
            console.print("  t - Temp")
            console.print("  o - obj")
            console.print("  g - Logs")
            console.print("  b - Build (if available)")

            # Show global cache options if available
            global_cache_options = {}
            for cache_name in report["cache_dirs"].keys():
                if cache_name not in ["Library", "Temp", "obj", "Logs", "Build"]:
                    option_key = cache_name.lower()[:1]  # First letter as option
                    if option_key not in ["a", "p", "l", "t", "o", "g", "b"]:
                        global_cache_options[option_key] = cache_name
                        console.print(f"  {option_key} - {cache_name}")

            choices = (
                input("Enter choices separated by commas (e.g., a,p,l): ")
                .strip()
                .lower()
                .split(",")
            )

            logger.info(
                "User selected Unity cache cleanup options",
                extra={"project_name": project["name"], "choices": choices},
            )

            # Determine directories to clear
            directories_to_clear = []
            if "a" in choices:
                directories_to_clear = list(report["cache_dirs"].keys())
            elif "p" in choices:
                # Project caches only
                directories_to_clear = ["Library", "Temp", "obj", "Logs"]
            else:
                available_choices = {
                    "l": "Library",
                    "t": "Temp",
                    "o": "obj",
                    "g": "Logs",
                    "b": "Build",
                }
                # Add global cache options
                available_choices.update(global_cache_options)

                for choice in choices:
                    if choice in available_choices:
                        directories_to_clear.append(available_choices[choice])

            # Special handling for Build directory - add warnings
            if "Build" in directories_to_clear:
                console.print(f"\n{YELLOW}⚠️  WARNING: Build directory cleanup requested{YELLOW}")
                console.print(f"{YELLOW}Build directories contain compiled game assets and may take significant time to rebuild.{RESET}")
                console.print(f"{YELLOW}Backups will be created automatically before deletion.{RESET}")

                # Check config for build directory inclusion
                from ..core.config import get_typed_config
                config = get_typed_config()
                if not getattr(config.unity, 'include_build_dirs', False):
                    console.print(f"\n{RED}❌ Build directory cleanup is disabled in configuration.{RESET}")
                    console.print(f"{YELLOW}Enable 'include_build_dirs' in config to allow build cleanup.{RESET}")
                    directories_to_clear.remove("Build")

            total_freed = 0
            for cache_name in directories_to_clear:
                cache_info = report["cache_dirs"][cache_name]
                if cache_info["exists"]:
                    try:
                        size_before = cache_info["size"]

                        # Enhanced logging with Unity version context
                        unity_version = report.get('unity_version', 'unknown')
                        cache_type = "global" if cache_name not in ["Library", "Temp", "obj", "Logs", "Build"] else "project"

                        # Special warning for Library directory
                        if cache_name == "Library":
                            logger.warning(
                                "Unity Library directory cleanup initiated - rebuild required",
                                extra={
                                    "project_name": project["name"],
                                    "cache_name": cache_name,
                                    "unity_version": unity_version,
                                    "cache_size": size_before,
                                    "warning": "Library cleanup will require full project rebuild",
                                    "estimated_rebuild_time": "high",
                                },
                            )
                            console.print(f"{YELLOW}⚠️  WARNING: Cleaning Library directory will require a full project rebuild!{RESET}")

                        logger.info(
                            "Starting Unity cache deletion",
                            extra={
                                "project_name": project["name"],
                                "cache_name": cache_name,
                                "cache_path": cache_info["path"],
                                "cache_size": size_before,
                                "cache_type": cache_type,
                                "unity_version": unity_version,
                                "rebuild_impact": _get_cache_impact_description(cache_name, size_before),
                            },
                        )

                        # Use secure deletion for safe removal with backups and audit trails
                        result = secure_delete(
                            [cache_info["path"]], f"Unity Cache Cleanup - {cache_name}"
                        )

                        if result.success:
                            total_freed += size_before
                            console.print(f"{GREEN}✓ Cleared: {cache_name}{RESET}")

                            # Log detailed success with Unity context
                            logger.info(
                                "Unity cache deletion successful",
                                extra={
                                    "project_name": project["name"],
                                    "cache_name": cache_name,
                                    "cache_type": cache_type,
                                    "unity_version": unity_version,
                                    "size_freed": size_before,
                                    "backup_created": bool(result.details.get("backup_paths")),
                                    "rebuild_impact": _get_cache_impact_description(cache_name, size_before),
                                },
                            )
                        else:
                            error_msg = (
                                result.errors[0] if result.errors else "Unknown error during secure deletion"
                            )
                            console.print(
                                f"{RED}✗ Failed to clear {cache_name}: {error_msg}{RESET}"
                            )
                            logger.error(
                                "Unity cache deletion failed",
                                extra={
                                    "project_name": project["name"],
                                    "cache_name": cache_name,
                                    "cache_type": cache_type,
                                    "unity_version": unity_version,
                                    "error": error_msg,
                                    "cache_size": size_before,
                                },
                            )
                    except Exception as e:
                        console.print(
                            f"{RED}✗ Failed to clear {cache_name}: {e}{RESET}"
                        )
                        logger.error(
                            "Unity cache deletion exception",
                            extra={
                                "project_name": project["name"],
                                "cache_name": cache_name,
                                "error": str(e),
                            },
                            exc_info=True,
                        )

            console.print("Selected cache directories have been processed.")
            logger.info(
                "Unity project processing completed",
                extra={"project_name": project["name"], "total_freed": total_freed},
            )

    except Exception as e:
        logger.error(
            "Unity Hub scanner failed",
            extra={"error": str(e), "operation": "unity_hub_scan"},
            exc_info=True,
        )
        raise
