#!/usr/bin/env python3
"""
Unity Engine project discovery and cache management for LazyScan.
"""

import os
import random
import sys
import threading
from typing import List, Dict, Any, Optional

from ..core.logging_config import get_logger
from ..core.formatting import human_readable, get_terminal_colors
from ..core.ui import knight_rider_animation, get_random_funny_message, get_console
from ..core.config import get_config
from helpers.unity_cache_helpers import generate_unity_project_report
from helpers.unity_hub import read_unity_hub_projects
from helpers.secure_operations import secure_delete


logger = get_logger(__name__)
console = get_console()


def prompt_unity_project_selection(projects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Prompt user to select Unity projects."""
    logger.info("Prompting user for Unity project selection", extra={
        "operation": "project_selection",
        "project_count": len(projects),
        "interactive": sys.stdin.isatty()
    })
    
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
        selection = input("Select projects by number (comma or space-separated): ").strip()
        if selection.strip().lower() == 'q':
            logger.info("User quit project selection")
            return []

        try:
            indexes = set(
                int(x) for x in selection.replace(',', ' ').split() if x.isdigit()
            )

            if 0 in indexes:
                logger.info("User selected all projects")
                return projects

            selected_projects = [projects[i - 1] for i in indexes if 0 < i <= len(projects)]

            if not selected_projects:
                console.print("No valid selections made. Please try again.")
                logger.warning("No valid project selections made", extra={"input": selection})
        except ValueError as e:
            console.print("Invalid input. Please enter numbers separated by commas or spaces.")
            logger.warning("Invalid project selection input", extra={
                "input": selection,
                "error": str(e)
            })

    logger.info("User selected Unity projects", extra={
        "selected_count": len(selected_projects),
        "selected_projects": [p['name'] for p in selected_projects]
    })
    
    return selected_projects


def handle_unity_discovery(args) -> None:
    """Handle the discovery and processing of Unity projects."""
    logger.info("Starting Unity project discovery", extra={
        "operation": "unity_discovery",
        "no_unityhub": args.no_unityhub,
        "clean_mode": args.clean
    })
    
    handle_unity_projects_integration(args)


def handle_unity_projects_integration(args) -> None:
    """Handle the discovery of Unity projects via Unity Hub and existing methodologies."""
    logger.debug("Handling Unity projects integration", extra={
        "no_unityhub": args.no_unityhub
    })
    
    if not args.no_unityhub:
        return scan_unity_project_via_hub(args, clean=args.clean)
    else:
        logger.info("Unity Hub disabled, falling back to directory picker")
        from ..core.scanner import default_directory_picker
        return default_directory_picker()


def scan_unity_project_via_hub(args, clean: bool = False) -> None:
    """Scan Unity projects via Unity Hub and generate a report."""
    colors = get_terminal_colors()
    CYAN, MAGENTA, YELLOW, RESET, BOLD, BRIGHT_CYAN, BRIGHT_MAGENTA, GREEN, RED = colors[:9]
    
    logger.info("Starting Unity Hub scanner", extra={
        "operation": "unity_hub_scan",
        "clean_mode": clean,
        "unityhub_json": getattr(args, 'unityhub_json', None)
    })

    console.print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}UNITY HUB SCANNER{CYAN}]{RESET} {YELLOW}Discovering Unity projects via Unity Hub...{RESET}")

    # Select a random funny message
    funny_msg = get_random_funny_message()

    # Show animation while discovering projects
    projects = []
    discovery_done = False

    def discover_unity_projects():
        nonlocal projects, discovery_done
        try:
            unity_hub_json_path = args.unityhub_json if args.unityhub_json else None
            projects = read_unity_hub_projects(unity_hub_json_path)
            logger.info("Unity project discovery completed", extra={
                "project_count": len(projects),
                "json_path": unity_hub_json_path
            })
        except Exception as e:
            logger.error("Unity project discovery failed", extra={
                "error": str(e),
                "json_path": getattr(args, 'unityhub_json', None)
            })
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
        logger.error("Unity project discovery failed with exception", extra={
            "exception_type": type(projects).__name__,
            "error": str(projects)
        })
        raise projects

    try:
        unity_hub_json_path = args.unityhub_json if args.unityhub_json else None

        if not projects:
            console.print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}No Unity projects found in Unity Hub.{RESET}")
            logger.warning("No Unity projects found in Unity Hub")
            return

        console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}✓{CYAN}]{RESET} {GREEN}Found {len(projects)} Unity projects in Unity Hub.{RESET}")

        # Prompt user to select projects if not in clean mode or if there are multiple projects
        selected_projects = []
        if clean and not args.pick and len(projects) > 0:
            # If in clean mode and not forcing pick, assume all projects are to be cleaned
            selected_projects = projects
            logger.info("Auto-selecting all projects for cleaning")
        else:
            selected_projects = prompt_unity_project_selection(projects)

        if not selected_projects:
            console.print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}No Unity projects selected. Aborting scan.{RESET}")
            logger.warning("No Unity projects selected, aborting scan")
            return

        console.print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}UNITY SCANNER{CYAN}]{RESET} {YELLOW}Generating Unity Project Reports...{RESET}")
        logger.info("Starting Unity project report generation", extra={
            "selected_count": len(selected_projects)
        })

        for project in selected_projects:
            logger.debug("Processing Unity project", extra={
                "project_name": project['name'],
                "project_path": project['path']
            })
            
            report = generate_unity_project_report(
                project['path'],
                project['name'],
                include_build=args.build_dir
            )

            # Display the report
            console.print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}PROJECT{CYAN}]{RESET} {YELLOW}{report['name']}{RESET}")
            console.print(f"{CYAN}Path:{RESET} {GREEN}{report['path']}{RESET}")
            console.print(f"{CYAN}Total Cache Size:{RESET} {BRIGHT_MAGENTA}{human_readable(report['total_size'])}{RESET}")

            # Display individual cache directories
            console.print(f"\n{CYAN}Cache Directories:{RESET}")
            for cache_name, cache_info in report['cache_dirs'].items():
                if cache_info['exists']:
                    console.print(f"  {GREEN}✓{RESET} {cache_name}: {BRIGHT_MAGENTA}{human_readable(cache_info['size'])}{RESET}")
                else:
                    console.print(f"  {YELLOW}✗{RESET} {cache_name}: {YELLOW}Not found{RESET}")

            console.print()

            # Ask if the user wants to clear cache directories
            # Options for clearing specific cache types
            console.print("Choose which cache directories to clear:")
            console.print("  a - All")
            console.print("  l - Library")
            console.print("  t - Temp")
            console.print("  o - obj")
            console.print("  g - Logs")
            choices = input("Enter choices separated by commas (e.g., a,l,t): ").strip().lower().split(",")

            logger.info("User selected Unity cache cleanup options", extra={
                "project_name": project['name'],
                "choices": choices
            })

            # Determine directories to clear
            directories_to_clear = []
            if 'a' in choices:
                directories_to_clear = list(report['cache_dirs'].keys())
            else:
                available_choices = {'l': 'Library', 't': 'Temp', 'o': 'obj', 'g': 'Logs'}
                for choice in choices:
                    if choice in available_choices:
                        directories_to_clear.append(available_choices[choice])

            total_freed = 0
            for cache_name in directories_to_clear:
                cache_info = report['cache_dirs'][cache_name]
                if cache_info['exists']:
                    try:
                        size_before = cache_info['size']
                        
                        logger.info("Starting Unity cache deletion", extra={
                            "project_name": project['name'],
                            "cache_name": cache_name,
                            "cache_path": cache_info['path'],
                            "cache_size": size_before
                        })
                        
                        # Use secure deletion for safe removal with backups and audit trails
                        result = secure_delete([cache_info['path']], f"Unity Cache Cleanup - {cache_name}")

                        if result.success:
                            total_freed += size_before
                            console.print(f"{GREEN}✓ Cleared: {cache_name}{RESET}")
                            logger.info("Unity cache deletion successful", extra={
                                "project_name": project['name'],
                                "cache_name": cache_name,
                                "size_freed": size_before
                            })
                        else:
                            error_msg = result.error or "Unknown error during secure deletion"
                            console.print(f"{RED}✗ Failed to clear {cache_name}: {error_msg}{RESET}")
                            logger.error("Unity cache deletion failed", extra={
                                "project_name": project['name'],
                                "cache_name": cache_name,
                                "error": error_msg
                            })
                    except Exception as e:
                        console.print(f"{RED}✗ Failed to clear {cache_name}: {e}{RESET}")
                        logger.error("Unity cache deletion exception", extra={
                            "project_name": project['name'],
                            "cache_name": cache_name,
                            "error": str(e)
                        }, exc_info=True)

            console.print("Selected cache directories have been processed.")
            logger.info("Unity project processing completed", extra={
                "project_name": project['name'],
                "total_freed": total_freed
            })

    except Exception as e:
        logger.error("Unity Hub scanner failed", extra={
            "error": str(e),
            "operation": "unity_hub_scan"
        }, exc_info=True)
        raise
