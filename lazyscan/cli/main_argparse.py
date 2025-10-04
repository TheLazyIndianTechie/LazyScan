#!/usr/bin/env python3
"""
Main CLI module for LazyScan.
Handles argument parsing, main execution flow, and coordination between modules.
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

from ..core.logging_config import (
    get_logger, get_console, setup_development_logging,
    log_cleanup_operation, log_scan_operation, log_operation
)
from ..core.formatting import human_readable, get_terminal_colors, ProgressDisplay
from ..core.errors import (
    cli_error_handler,
)
from ..core.ui import (
    show_logo,
    show_disclaimer,
    knight_rider_animation,
    display_scan_results_header,
    display_scan_summary,
    display_cache_cleanup_summary,
)
from ..core.config import (
    has_seen_disclaimer,
    mark_disclaimer_acknowledged,
    get_scanning_setting,
    get_ui_setting,
    get_config,
    update_config,
    reset_config,
    get_config_info,
    get_typed_config,
    get_setting,
)
from ..core.scanner import get_system_disk_usage, scan_directory_with_progress
from ..core.scan import scan_directory, scan_directory_sync
from ..apps.unity import handle_unity_discovery
from ..apps.unreal import handle_unreal_discovery
from ..apps.chrome import handle_chrome_discovery

# Import security framework
from helpers.audit import audit_logger
from helpers.secure_operations import configure_security
from helpers.recovery import get_recovery_stats, register_operation_for_recovery


logger = get_logger(__name__)
console = get_console()
__version__ = "0.6.0-beta"

# Platform-specific imports
if sys.platform == "darwin":
    from ..platforms.macos import (
        MACOS_CACHE_PATHS as SYSTEM_CACHE_PATHS,
        PERPLEXITY_PATHS,
        DIA_PATHS,
        SLACK_PATHS,
        DISCORD_PATHS,
        SPOTIFY_PATHS,
        VSCODE_PATHS,
        ZOOM_PATHS,
        TEAMS_PATHS,
        FIREFOX_PATHS,
        SAFARI_PATHS,
    )
elif sys.platform == "win32":
    from ..platforms.windows import (
        WINDOWS_CACHE_PATHS as SYSTEM_CACHE_PATHS,
        PERPLEXITY_PATHS,
        DIA_PATHS,
        SLACK_PATHS,
        DISCORD_PATHS,
        SPOTIFY_PATHS,
        VSCODE_PATHS,
        ZOOM_PATHS,
        TEAMS_PATHS,
        FIREFOX_PATHS,
        SAFARI_PATHS,
    )
else:
    from ..platforms.linux import (
        LINUX_CACHE_PATHS as SYSTEM_CACHE_PATHS,
        PERPLEXITY_PATHS,
        DIA_PATHS,
        SLACK_PATHS,
        DISCORD_PATHS,
        SPOTIFY_PATHS,
        VSCODE_PATHS,
        ZOOM_PATHS,
        TEAMS_PATHS,
        FIREFOX_PATHS,
        SAFARI_PATHS,
    )


def initialize_security_system():
    """Initialize the comprehensive security framework for LazyScan."""
    try:
        logger.info(
            "Initializing security system",
            extra={"version": __version__, "platform": sys.platform},
        )

        # Initialize SecuritySentinel first (critical security component)
        from ..security.sentinel import initialize_sentinel, startup_health_check
        initialize_sentinel()
        startup_health_check()

        # Log application startup
        audit_logger.log_startup(
            {
                "version": __version__,
                "security_enabled": True,
                "backup_enabled": True,
                "platform": sys.platform,
            }
        )

        # Configure security settings
        configure_security(enable_backups=True, enable_confirmations=True)

        # Show recovery statistics if available
        stats = get_recovery_stats()
        if stats["recoverable_operations"] > 0:
            console.print(
                f"\n🔄 Recovery System: {stats['recoverable_operations']} operations can be recovered"
            )
            console.print(
                f"   Total recoverable: {stats['total_files_recoverable']:,} files ({stats['total_size_recoverable'] / (1024**3):.1f} GB)"
            )

        return True
    except Exception as e:
        logger.error(
            "Security system initialization failed",
            extra={"error": str(e)},
            exc_info=True,
        )
        console.print(f"⚠️  Warning: Security system initialization failed: {e}")
        console.print("   Continuing with basic safety measures...")
        return False


def clean_cache(paths, colors, app_name=None, check_path=None, dry_run=False, force=False, permanent=False):
    """Generic function to scan and clean cache directories."""
    import glob
    import shutil

    CYAN, MAGENTA, YELLOW, RESET, BOLD, BRIGHT_CYAN, BRIGHT_MAGENTA, GREEN, RED = (
        get_terminal_colors()[:9]
    )

    if app_name:
        console.print(
            f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}{app_name.upper()}{CYAN}]{RESET} {YELLOW}Scanning {app_name} cache...{RESET}"
        )
    else:
        console.print(
            f"\n{BOLD}{CYAN}[{MAGENTA}►{CYAN}]{RESET} {YELLOW}Scanning cache directories...{RESET}"
        )

    if check_path and not os.path.exists(os.path.expanduser(check_path)):
        console.print(
            f"\n{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}{app_name} not found or not installed.{RESET}"
        )
        return 0

    cache_items = []
    for path_pattern in paths:
        expanded_pattern = os.path.expanduser(path_pattern)
        for item in glob.glob(expanded_pattern):
            if os.path.exists(item):
                try:
                    if os.path.isfile(item):
                        size = os.path.getsize(item)
                        cache_items.append((item, size, "file"))
                    elif os.path.isdir(item):
                        size = sum(
                            os.path.getsize(os.path.join(root, f))
                            for root, dirs, files in os.walk(item)
                            for f in files
                        )
                        cache_items.append((item, size, "dir"))
                    else:
                        continue
                except (OSError, PermissionError):
                    continue

    if not cache_items:
        if app_name:
            console.print(
                f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}No {app_name} cache found.{RESET}"
            )
        else:
            console.print(
                f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}No cache items found to clean.{RESET}"
            )
        return 0

    total_size = sum(size for _, size, _ in cache_items)
    if app_name:
        console.print(
            f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}✓{CYAN}]{RESET} {GREEN}Found {len(cache_items)} {app_name} cache items ({BRIGHT_MAGENTA}{human_readable(total_size)}{RESET})"
        )
    else:
        console.print(
            f"\n{BOLD}{CYAN}[{MAGENTA}📊{CYAN}]{RESET} {YELLOW}Found {len(cache_items)} cache items ({human_readable(total_size)}){RESET}"
        )

    cache_items.sort(key=lambda x: x[1], reverse=True)
    for path, size, _ in cache_items[:5]:
        display_path = path.replace(os.path.expanduser("~"), "~")
        if len(display_path) > 60:
            display_path = "..." + display_path[-57:]
        console.print(f"  {human_readable(size):>10} {YELLOW}{display_path}{RESET}")

    if len(cache_items) > 5:
        console.print(f"  ...and {len(cache_items) - 5} more items")

    if (
        not input(f"\n{YELLOW}Clean {len(cache_items)} cache items? [y/N]: {RESET}")
        .strip()
        .lower()
        .startswith("y")
    ):
        console.print(
            f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}Cache cleaning cancelled.{RESET}"
        )
        return 0

    # Register operation for recovery before deletion
    import time
    from pathlib import Path
    import tempfile

    operation_id = f"cache_cleanup_{app_name.lower().replace(' ', '_') if app_name else 'general'}_{int(time.time())}"
    original_paths = [path for path, _, _ in cache_items]
    backup_paths = []

    # Create backups for recovery
    backup_dir = Path(tempfile.gettempdir()) / "lazyscan_backups" / operation_id
    backup_dir.mkdir(parents=True, exist_ok=True)

    for path, size, item_type in cache_items:
        try:
            backup_path = backup_dir / Path(path).name
            if item_type == "file" and os.path.isfile(path):
                shutil.copy2(path, backup_path)
                backup_paths.append(str(backup_path))
            elif item_type == "dir" and os.path.isdir(path):
                shutil.copytree(path, backup_path, dirs_exist_ok=True)
                backup_paths.append(str(backup_path))
        except Exception as e:
            logger.warning(f"Failed to create backup for {path}: {e}")

    # Register the operation
    register_operation_for_recovery(
        operation_id=operation_id,
        operation_type=f"{app_name or 'General'} Cache Cleanup",
        original_paths=original_paths,
        backup_paths=backup_paths,
        files_affected=len(cache_items),
        size_affected=total_size,
        metadata={"app_name": app_name, "cleanup_mode": "cache"}
    )

    with log_operation("cache_cleanup", app_name=app_name, operation_id=operation_id, items_to_clean=len(cache_items)):
        knight_rider_animation(f'Cleaning {app_name or "cache"}...', colors=colors)

        freed_bytes = 0
        errors = 0

        # Import SafeDeleter for secure deletion
        from ..security.safe_delete import get_safe_deleter, DeletionMode

        deleter = get_safe_deleter()
        deletion_mode = DeletionMode.TRASH if not permanent else DeletionMode.PERMANENT

        for path, size, item_type in cache_items:
            try:
                # Use SafeDeleter for all deletion operations
                success = deleter.delete(
                    Path(path),
                    mode=deletion_mode,
                    dry_run=dry_run,
                    force=force,
                    context=f"{app_name or 'general'}_cache_cleanup"
                )
                if success or dry_run:
                    freed_bytes += size
                else:
                    errors += 1
            except Exception as e:
                logger.warning(f"Failed to delete {path}: {e}")
                errors += 1

        sys.stdout.write("\r" + " " * 100 + "\r")
        sys.stdout.flush()

        if app_name:
            console.print(
                f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}✓{CYAN}]{RESET} {BRIGHT_CYAN}{app_name.upper()} CACHE CLEANED{RESET}"
            )
            console.print(
                f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Space reclaimed:{RESET} {BRIGHT_MAGENTA}{human_readable(freed_bytes)}{RESET}"
            )
            console.print(
                f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Items cleaned:{RESET} {BRIGHT_CYAN}{len(cache_items) - errors}{RESET}"
            )

        if errors > 0:
            console.print(
                f"{BOLD}{CYAN}[{RED}!{CYAN}]{RESET} {RED}Failed to clean {errors} items (permission denied){RESET}"
            )

        console.print(
            f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}■{CYAN}]{RESET} {GREEN}{app_name or 'Cache'} cleanup completed successfully.{RESET}"
        )

        # Log cleanup operation
        # Temporarily commented out for debugging
        # log_cleanup_operation(
        #     app_name=app_name or "general",
        #     files_cleaned=len(cache_items) - errors,
        #     size_cleaned=freed_bytes,
        #     errors=errors
        # )
    # End of with block

    return freed_bytes


def select_directory():
    """Let the user choose a directory from stdin."""
    cwd = os.getcwd()
    dirs = ["."] + sorted(
        [d for d in os.listdir(cwd) if os.path.isdir(os.path.join(cwd, d))]
    )
    console.print("Select directory to scan:")
    for idx, d in enumerate(dirs, start=1):
        console.print(f"  {idx}. {d}")
    console.print("  0. Enter custom path")

    while True:
        choice = input(f"Choice [0-{len(dirs)}]: ").strip()
        if not choice.isdigit():
            console.print("Please enter a number.")
            continue
        n = int(choice)
        if n == 0:
            custom = input("Enter path to scan: ").strip()
            return custom
        if 1 <= n <= len(dirs):
            return dirs[n - 1]
        console.print(f"Invalid choice: {choice}")


def clean_macos_cache(paths, colors):
    """Clean macOS cache directories."""
    import glob

    CYAN, MAGENTA, YELLOW, RESET, BOLD = colors[:5]

    console.print(
        f"\n{BOLD}{CYAN}[{MAGENTA}►{CYAN}]{RESET} {YELLOW}Scanning cache directories...{RESET}"
    )

    cache_items = []
    for path_pattern in paths:
        expanded_pattern = os.path.expanduser(path_pattern)
        for item in glob.glob(expanded_pattern):
            if os.path.exists(item):
                try:
                    if os.path.isfile(item):
                        size = os.path.getsize(item)
                    elif os.path.isdir(item):
                        size = sum(
                            os.path.getsize(os.path.join(root, f))
                            for root, dirs, files in os.walk(item)
                            for f in files
                        )
                    else:
                        continue
                    cache_items.append((item, size))
                except (OSError, PermissionError):
                    continue

    if not cache_items:
        console.print(
            f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}No cache items found to clean.{RESET}"
        )
        return 0

    # Sort by size
    cache_items.sort(key=lambda x: x[1], reverse=True)
    total_size = sum(size for _, size in cache_items)

    console.print(
        f"\n{BOLD}{CYAN}[{MAGENTA}📊{CYAN}]{RESET} {YELLOW}Found {len(cache_items)} cache items ({human_readable(total_size)}){RESET}"
    )

    # Show top 5 items
    console.print(f"\n{CYAN}Top cache items:{RESET}")
    for path, size in cache_items[:5]:
        display_path = path.replace(os.path.expanduser("~"), "~")
        console.print(f"  {human_readable(size):>10} {display_path}")

    if len(cache_items) > 5:
        console.print(f"  ...and {len(cache_items) - 5} more items")

    # Confirm deletion
    if (
        not input(f"\n{YELLOW}Clean {len(cache_items)} cache items? [y/N]: {RESET}")
        .strip()
        .lower()
        .startswith("y")
    ):
        console.print(
            f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}Cache cleaning cancelled.{RESET}"
        )
        return 0

    # Animate deletion
    knight_rider_animation("Cleaning cache directories...", colors=colors)

    freed_bytes = 0
    errors = 0

    # Import SafeDeleter for secure deletion
    from ..security.safe_delete import get_safe_deleter, DeletionMode

    deleter = get_safe_deleter()
    deletion_mode = DeletionMode.TRASH  # macOS cache cleaning uses trash by default

    for path, size in cache_items:
        try:
            # Use SafeDeleter for all deletion operations
            success = deleter.delete(
                Path(path),
                mode=deletion_mode,
                dry_run=False,  # macOS cache cleaning doesn't have dry-run
                force=False,    # Requires confirmation above
                context="macos_cache_cleanup"
            )
            if success:
                freed_bytes += size
            else:
                errors += 1
        except Exception as e:
            logger.warning(f"Failed to delete {path}: {e}")
            errors += 1

    # Clear animation
    sys.stdout.write("\r" + " " * 100 + "\r")
    sys.stdout.flush()

    return freed_bytes


def scan_application_cache(app_name, paths, colors, check_path=None):
    """Scan application-specific cache directories."""
    CYAN, MAGENTA, YELLOW, RESET, BOLD, BRIGHT_CYAN, BRIGHT_MAGENTA, GREEN, RED = (
        get_terminal_colors()[:9]
    )

    # Check if application exists
    if check_path and not os.path.exists(os.path.expanduser(check_path)):
        console.print(
            f"\n{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}{app_name} not found or not installed.{RESET}"
        )
        return 0

    console.print(
        f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}{app_name.upper()}{CYAN}]{RESET} {YELLOW}Scanning {app_name} cache...{RESET}"
    )

    import glob

    cache_items = []

    for path_pattern in paths:
        for item in glob.glob(path_pattern):
            if os.path.exists(item):
                try:
                    if os.path.isfile(item):
                        size = os.path.getsize(item)
                        cache_items.append((item, size))
                    elif os.path.isdir(item):
                        dir_size = 0
                        for root, dirs, files in os.walk(item):
                            for file in files:
                                try:
                                    dir_size += os.path.getsize(
                                        os.path.join(root, file)
                                    )
                                except (OSError, PermissionError):
                                    continue
                        cache_items.append((item, dir_size))
                except (OSError, PermissionError):
                    continue

    if not cache_items:
        console.print(
            f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}No {app_name} cache found.{RESET}"
        )
        return 0

    # Calculate total
    total_size = sum(size for _, size in cache_items)
    console.print(
        f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}✓{CYAN}]{RESET} {GREEN}Found {len(cache_items)} {app_name} cache items ({BRIGHT_MAGENTA}{human_readable(total_size)}{RESET})"
    )

    # Show details
    cache_items.sort(key=lambda x: x[1], reverse=True)
    for path, size in cache_items[:3]:
        display_path = path.replace(os.path.expanduser("~"), "~")
        if len(display_path) > 60:
            display_path = "..." + display_path[-57:]
        console.print(f"  {human_readable(size):>10} {YELLOW}{display_path}{RESET}")

    if len(cache_items) > 3:
        console.print(f"  {CYAN}...and {len(cache_items) - 3} more items{RESET}")

    # Ask for confirmation
    response = (
        input(f"\n{YELLOW}Clean {app_name} cache? [y/N]: {RESET}").strip().lower()
    )
    if not response.startswith("y"):
        console.print(
            f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}{app_name} cleanup cancelled.{RESET}"
        )
        return 0

    # Clean with animation
    knight_rider_animation(f"Cleaning {app_name} cache...", colors=colors[:5])

    freed_bytes = 0
    errors = 0

    # Import SafeDeleter for secure deletion
    from ..security.safe_delete import get_safe_deleter, DeletionMode

    deleter = get_safe_deleter()
    deletion_mode = DeletionMode.TRASH  # App cache cleaning uses trash by default

    for path, size in cache_items:
        try:
            # Use SafeDeleter for all deletion operations
            success = deleter.delete(
                Path(path),
                mode=deletion_mode,
                dry_run=False,  # App cache cleaning doesn't have dry-run
                force=False,    # Requires confirmation above
                context=f"{app_name}_cache_cleanup"
            )
            if success:
                freed_bytes += size
            else:
                errors += 1
        except Exception as e:
            logger.warning(f"Failed to delete {path}: {e}")
            errors += 1

    # Clear animation
    sys.stdout.write("\r" + " " * 100 + "\r")
    sys.stdout.flush()

    # Results
    console.print(
        f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}✓{CYAN}]{RESET} {BRIGHT_CYAN}{app_name.upper()} CACHE CLEANED{RESET}"
    )
    console.print(
        f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Space reclaimed:{RESET} {BRIGHT_MAGENTA}{human_readable(freed_bytes)}{RESET}"
    )
    console.print(
        f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Items cleaned:{RESET} {BRIGHT_CYAN}{len(cache_items) - errors}{RESET}"
    )

    if errors > 0:
        console.print(
            f"{BOLD}{CYAN}[{RED}!{CYAN}]{RESET} {RED}Failed to clean {errors} items (permission denied){RESET}"
        )

        console.print(
            f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}■{CYAN}]{RESET} {GREEN}{app_name} cleanup completed successfully.{RESET}"
        )

        # Log cleanup operation
        log_cleanup_operation(
            app_name=app_name or "general",
            files_cleaned=len(cache_items) - errors,
            size_cleaned=freed_bytes,
            errors=errors
        )

    return freed_bytes


def create_argument_parser():
    """Create and configure the argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        description="A lazy way to find what's eating your disk space with added support for macOS cache cleaning",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Scan your home directory and show top 10 biggest files:
    lazyscan scan ~ -n 10

  Scan current directory with interactive selection:
    lazyscan scan -i

  Clean macOS cache directories (macOS only):
    lazyscan clean macos

  Clean Unity cache:
    lazyscan clean unity

  Clean cache and then scan Downloads folder:
    lazyscan clean macos && lazyscan scan ~/Downloads

  Scan Chrome browser cache (macOS only):
    lazyscan scan chrome

  Scan Unreal Engine projects:
    lazyscan scan unreal

  Show recovery options:
    lazyscan recovery

  Show version:
    lazyscan --version
""",
    )

    # Global options
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="show version number and exit",
    )
    parser.add_argument(
        "--no-disclaimer",
        action="store_true",
        help="skip disclaimer acknowledgment (for automation)",
    )

    # Create subparsers
    subparsers = parser.add_subparsers(
        dest="command",
        help="Available commands",
        required=True
    )

    # Scan command
    scan_parser = subparsers.add_parser(
        "scan",
        help="Scan directories and files for disk usage analysis"
    )
    scan_parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help="directory path to scan (default: current directory)",
    )
    scan_parser.add_argument(
        "-n",
        "--top",
        type=int,
        default=get_scanning_setting("top_files", 20),
        help=f"number of top files to display (default: {get_scanning_setting('top_files', 20)})",
    )
    scan_parser.add_argument(
        "-w",
        "--width",
        type=int,
        default=get_ui_setting("bar_width", 40),
        help=f"bar width in characters (default: {get_ui_setting('bar_width', 40)})",
    )
    scan_parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="prompt to choose directory (for the truly lazy)",
    )
    scan_parser.add_argument(
        "--no-logo",
        action="store_true",
        help="hide the lazyscan logo"
    )
    scan_parser.add_argument(
        "--json",
        action="store_true",
        help="output results in JSON format"
    )
    scan_parser.add_argument(
        "--exclude",
        action="append",
        help="patterns to exclude from scan (can be used multiple times)",
    )
    scan_parser.add_argument(
        "--min-size",
        type=str,
        help="minimum file size to include (e.g., '1MB', '500KB', '2GB')",
    )

    # Application-specific scan options
    scan_parser.add_argument(
        "--chrome",
        action="store_true",
        help="scan Chrome Application Support for cleanable files",
    )
    scan_parser.add_argument(
        "--unity",
        action="store_true",
        help="scan Unity projects and cache",
    )
    scan_parser.add_argument(
        "--unreal",
        action="store_true",
        help="scan Unreal Engine projects",
    )
    scan_parser.add_argument(
        "--firefox",
        action="store_true",
        help="scan Firefox cache for cleanable files"
    )
    scan_parser.add_argument(
        "--vscode",
        action="store_true",
        help="scan VS Code cache for cleanable files"
    )

    # Clean command
    clean_parser = subparsers.add_parser(
        "clean",
        help="Clean cache directories and temporary files"
    )
    clean_parser.add_argument(
        "target",
        choices=["macos", "unity", "chrome", "firefox", "vscode", "all"],
        help="what to clean",
    )
    clean_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show what would be cleaned without actually deleting",
    )
    clean_parser.add_argument(
        "--force",
        action="store_true",
        help="skip confirmation prompts (dangerous)",
    )
    clean_parser.add_argument(
        "--permanent",
        action="store_true",
        help="permanently delete instead of moving to trash",
    )

    # System cache command
    cache_parser = subparsers.add_parser(
        "cache",
        help="Manage system-wide cache cleanup with retention policies"
    )
    cache_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show what would be cleaned without actually deleting",
    )
    cache_parser.add_argument(
        "--force",
        action="store_true",
        help="skip safety confirmations for dangerous operations",
    )
    cache_parser.add_argument(
        "--include-docker",
        action="store_true",
        help="include Docker container cleanup (requires confirmation)",
    )
    cache_parser.add_argument(
        "--targets",
        nargs="*",
        choices=["homebrew", "npm", "pip", "docker", "apt", "yum", "pacman", "tmp", "temp", "prefetch", "thumbnail", "installer"],
        help="specific cache targets to clean (default: all safe targets)",
    )
    cache_parser.add_argument(
        "--platform",
        choices=["macos", "linux", "windows", "auto"],
        default="auto",
        help="target platform (default: auto-detect)",
    )

    # Recovery command
    recovery_parser = subparsers.add_parser(
        "recovery",
        help="Manage file recovery and audit logs"
    )
    recovery_parser.add_argument(
        "action",
        nargs="?",
        choices=["list", "restore", "stats", "logs"],
        default="list",
        help="recovery action to perform",
    )
    recovery_parser.add_argument(
        "--operation-id",
        help="specific operation ID to restore",
    )

    # Config command
    config_parser = subparsers.add_parser(
        "config",
        help="Manage LazyScan configuration"
    )
    config_parser.add_argument(
        "action",
        choices=["get", "set", "list", "reset", "info"],
        help="configuration action to perform",
    )
    config_parser.add_argument(
        "key",
        nargs="?",
        help="configuration key (for get/set actions)",
    )
    config_parser.add_argument(
        "value",
        nargs="?",
        help="configuration value (for set action)",
    )
    config_parser.add_argument(
        "--app",
        help="application-specific configuration (for per-app overrides)",
    )

    return parser


def parse_size_string(size_str: str) -> int:
    """Parse human-readable size string to bytes."""
    if not size_str:
        return 0

    # Remove spaces and convert to uppercase
    size_str = size_str.replace(" ", "").upper()

    # Extract number and unit
    import re
    match = re.match(r'^(\d+(?:\.\d+)?)([KMGT]?B?)$', size_str)
    if not match:
        raise ValueError(f"Invalid size format: {size_str}")

    number = float(match.group(1))
    unit = match.group(2)

    # Convert to bytes
    multipliers = {
        'B': 1,
        'KB': 1024,
        'MB': 1024**2,
        'GB': 1024**3,
        'TB': 1024**4,
    }

    # Handle cases like "1M" or "1MB"
    if unit in ['K', 'M', 'G', 'T']:
        unit += 'B'

    if unit not in multipliers:
        raise ValueError(f"Unknown size unit: {unit}")

    return int(number * multipliers[unit])


def apply_filters(file_sizes: list, exclude_patterns: Optional[list] = None, min_size_str: Optional[str] = None) -> list:
    """Apply filtering to file sizes list."""
    import fnmatch
    import os

    filtered = file_sizes.copy()

    # Apply minimum size filter
    if min_size_str:
        try:
            min_size = parse_size_string(min_size_str)
            filtered = [(path, size) for path, size in filtered if size >= min_size]
        except ValueError as e:
            console.print(f"Warning: Invalid min-size format '{min_size_str}': {e}")
            console.print("Ignoring min-size filter.")

    # Apply exclude patterns
    if exclude_patterns:
        excluded = []
        for pattern in exclude_patterns:
            # Support glob patterns
            for path, size in filtered:
                filename = os.path.basename(path)

                # Check if pattern matches filename or full path
                if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(path, pattern):
                    excluded.append((path, size))

        # Remove excluded files
        for excluded_file in excluded:
            if excluded_file in filtered:
                filtered.remove(excluded_file)

    return filtered


def handle_scan_command(args):
    """Handle the scan subcommand."""
    # Handle engine-specific discovery
    if args.unity:
        logger.info("Starting Unity discovery")
        handle_unity_discovery(args)
        return

    if args.unreal:
        logger.info("Starting Unreal discovery")
        handle_unreal_discovery(args)
        return

    # Handle Chrome cache scanning
    if args.chrome:
        logger.info("Starting Chrome cache scanning")
        handle_chrome_discovery(args)
        # If only Chrome scanning was requested, exit
        if not args.path and not args.interactive:
            return

    # Setup colors for application scanning
    colors = get_terminal_colors()
    CYAN, MAGENTA, YELLOW, RESET, BOLD, BRIGHT_CYAN, BRIGHT_MAGENTA, GREEN, RED = colors[:9]

    # Handle application-specific cache scans
    app_scans_done = handle_application_specific_scans_legacy(args, colors)
    if app_scans_done and not args.path and not args.interactive:
        return

    # Determine scan path for directory scanning
    if args.interactive:
        scan_path = select_directory()
    else:
        scan_path = args.path or "."

    # Validate scan path for security
    from helpers.security import sanitize_input
    import os

    # Sanitize the input path
    scan_path = sanitize_input(scan_path, "path")

    # Basic validation for scanning (less restrictive than deletion)
    try:
        # Expand user path and resolve to absolute path
        expanded_path = os.path.realpath(os.path.expanduser(scan_path))

        # Check if path exists
        if not os.path.exists(expanded_path):
            logger.error(
                "Scan path does not exist",
                extra={"scan_path": scan_path, "expanded_path": expanded_path},
            )
            console.print(f"\n{BOLD}{RED}[ERROR]{RESET} {RED}Scan path does not exist: {scan_path}{RESET}")
            return

        # Check for obviously dangerous system paths
        dangerous_paths = ["/System", "/usr", "/bin", "/sbin", "/etc", "/private/etc"]
        for dangerous in dangerous_paths:
            if expanded_path.startswith(dangerous):
                logger.error(
                    "Dangerous system path rejected for scanning",
                    extra={"scan_path": scan_path, "expanded_path": expanded_path, "dangerous_prefix": dangerous},
                )
                console.print(f"\n{BOLD}{RED}[SECURITY VIOLATION]{RESET} {RED}System path rejected: {scan_path}{RESET}")
                console.print(f"{YELLOW}Scanning system directories is not allowed for security reasons.{RESET}")
                return

        # Check if it's a file (single file scanning)
        if os.path.isfile(expanded_path):
            logger.info("Single file scan requested", extra={"file_path": expanded_path})
        elif not os.path.isdir(expanded_path):
            logger.error(
                "Path is neither file nor directory",
                extra={"scan_path": scan_path, "expanded_path": expanded_path},
            )
            console.print(f"\n{BOLD}{RED}[ERROR]{RESET} {RED}Path is neither file nor directory: {scan_path}{RESET}")
            return

    except Exception as e:
        logger.error(
            "Path validation error",
            extra={"scan_path": scan_path, "error": str(e)},
            exc_info=True,
        )
        console.print(f"\n{BOLD}{RED}[ERROR]{RESET} {RED}Path validation failed: {str(e)}{RESET}")
        return

    logger.info(
        "Starting directory scan",
        extra={
            "scan_path": scan_path,
            "top_files": args.top,
            "interactive": args.interactive,
            "path_validated": True,
        },
    )

    # Perform directory scan with structured logging and UI
    with log_operation("directory_scan", scan_path=scan_path, interactive=args.interactive):
        # Use async scanning with progress callback
        progress_display = ProgressDisplay()

        async def progress_callback(path: Path, data: dict) -> None:
            """Async progress callback that updates the terminal display."""
            if isinstance(data, dict) and 'files_processed' in data:
                # Directory progress update
                rel_path = os.path.relpath(str(path), scan_path)
                rel_path = "." if rel_path == "." else f".../{rel_path}"
                await progress_display.update_progress_async(
                    "Scanning",
                    data.get('files_processed', 0),
                    data.get('total_files', 0) or 1,  # Avoid division by zero
                    extra_info=rel_path
                )

        # Run scan using synchronous wrapper for backward compatibility
        scan_result = scan_directory_sync(
            Path(scan_path),
            max_depth=None,  # TODO: Add max_depth support from args
            exclude_patterns=args.exclude,
            progress_callback=progress_callback
        )

        # Complete progress display
        progress_display.finish_progress("Scan completed")

        # Convert result format to match existing code expectations
        file_sizes = scan_result['files']

        if not file_sizes:
            console.print(f"No files found under '{scan_path}'.")
            logger.warning(
                "No files found in scan path", extra={"scan_path": scan_path}
            )
            return

        # Apply filters
        filtered_files = apply_filters(file_sizes, args.exclude, args.min_size)

        if not filtered_files:
            console.print("No files match the specified filters.")
            return

        # Sort and select top N files
        filtered_files.sort(key=lambda x: x[1], reverse=True)
        top_files = filtered_files[: args.top]
        total_size = sum(size for _, size in top_files)

        # Display results
        display_scan_results_header(len(top_files), colors)

        # Render results table
        from ..core.formatting import render_results_table

        if args.json:
            # JSON output mode
            import json
            results = {
                "scan_path": scan_path,
                "total_files": scan_result['file_count'],
                "total_dirs": scan_result['dir_count'],
                "total_size_bytes": scan_result['total_size'],
                "top_files_count": len(top_files),
                "files": [
                    {"path": path, "size_bytes": size, "size_human": human_readable(size)}
                    for path, size in top_files
                ],
                "errors": scan_result['errors']
            }
            console.print(json.dumps(results, indent=2))
        else:
            # Use responsive width if default value is used
            from ..core.config import get_ui_setting
            from ..core.ui import get_theme
            table_width = None if args.width == get_ui_setting("bar_width", 40) else args.width
            theme = get_theme()
            render_results_table(top_files, table_width, colors, theme.glyphs)

            # Display summary
            display_scan_summary(total_size, scan_path, colors)

        logger.info(
            "Directory scan completed",
            extra={
                "scan_path": scan_path,
                "files_found": scan_result['file_count'],
                "dirs_found": scan_result['dir_count'],
                "total_size": scan_result['total_size'],
                "top_files_shown": len(top_files),
                "errors": len(scan_result['errors']),
            },
        )

        # Log scan operation
        log_scan_operation(
            scan_path=scan_path,
            files_found=scan_result['file_count'],
            total_size=scan_result['total_size'],
            top_files_shown=len(top_files)
        )


def handle_clean_command(args):
    """Handle the clean subcommand."""
    colors = get_terminal_colors()

    if args.target == "macos":
        # Platform guard - macOS only feature
        if sys.platform != "darwin":
            logger.error(
                "macOS cache cleaning attempted on non-macOS platform",
                extra={"platform": sys.platform},
            )
            console.print("\nError: macOS cleaning is only available on macOS.")
            sys.exit(1)

        logger.info("Starting macOS cache cleaning", extra={"operation": "macos_cache_clean"})

        # Get disk usage before cleaning
        total_before, used_before, free_before, _ = get_system_disk_usage("/")

        # Display initial disk usage
        console.print(
            f"\n{colors[4]}{colors[0]}[{colors[5]}SYSTEM STATUS{colors[0]}]{colors[3]} {colors[2]}Current disk usage:{colors[3]}"
        )
        _, _, _, usage_before_str = get_system_disk_usage("/")
        console.print(usage_before_str)

        # Clean macOS cache directories
        freed_bytes = clean_macos_cache(SYSTEM_CACHE_PATHS, colors)

        # Get disk usage after cleaning
        total_after, used_after, free_after, _ = get_system_disk_usage("/")

        # Display summary banner if space was actually freed
        if freed_bytes > 0:
            display_cache_cleanup_summary(
                freed_bytes,
                used_before,
                used_after,
                total_before,
                total_after,
                free_before,
                free_after,
                colors,
            )

            # Display updated disk usage
            console.print(
                f"\n{colors[4]}{colors[0]}[{colors[5]}SYSTEM STATUS{colors[0]}]{colors[3]} {colors[2]}Updated disk usage:{colors[3]}"
            )
            _, _, _, usage_after_str = get_system_disk_usage("/")
            console.print(usage_after_str)

        logger.info(
            "macOS cache cleaning completed",
            extra={
                "freed_bytes": freed_bytes,
                "used_before": used_before,
                "used_after": used_after,
            },
        )

    else:
        # Use plugin-based cleaning
        from ..core.plugins import get_plugin_manager

        plugin_manager = get_plugin_manager()
        plugin = plugin_manager.get_plugin(args.target)

        if not plugin:
            console.print(f"Unknown target: {args.target}")
            console.print(f"Available targets: {', '.join(plugin_manager.list_plugins() + ['macos', 'all'])}")
            return

        # Show cleaning start
        colors = get_terminal_colors()
        CYAN, MAGENTA, YELLOW, RESET, BOLD, BRIGHT_CYAN, BRIGHT_MAGENTA, GREEN, RED = colors[:9]

        console.print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}{args.target.upper()} CLEAN{CYAN}]{RESET} {YELLOW}Starting {args.target} cache cleaning...{RESET}")

        # Execute clean operation
        result = plugin_manager.clean_with_plugin(args.target, dry_run=args.dry_run, force=args.force, permanent=args.permanent)

        if result["status"] == "success":
            console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}✓{CYAN}]{RESET} {GREEN}{args.target.title()} cleaning completed successfully!{RESET}")
            if result["cleaned_items"] > 0:
                console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Space reclaimed:{RESET} {BRIGHT_MAGENTA}{human_readable(result['total_size'])}{RESET}")
                console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Items cleaned:{RESET} {BRIGHT_CYAN}{result['cleaned_items']}{RESET}")

            if result.get("errors"):
                console.print(f"{BOLD}{CYAN}[{RED}!{CYAN}]{RESET} {RED}Failed to clean {len(result['errors'])} items{RESET}")

        elif result["status"] == "not_implemented":
            console.print(f"{YELLOW}{args.target.title()} cleaning is not yet implemented.{RESET}")

        else:
            console.print(f"{BOLD}{CYAN}[{RED}!{CYAN}]{RESET} {RED}{args.target.title()} cleaning failed: {result['message']}{RESET}")

        logger.info(
            f"{args.target} cleaning completed",
            extra={
                "target": args.target,
                "status": result["status"],
                "cleaned_items": result.get("cleaned_items", 0),
                "total_size": result.get("total_size", 0),
                "errors": len(result.get("errors", [])),
            },
        )


def handle_recovery_command(args):
    """Handle the recovery subcommand."""
    if args.action == "list" or not args.action:
        console.print("\n=== Recovery System ===")
        stats = get_recovery_stats()
        console.print(
            f"Total recoverable operations: {stats.get('total_operations', 0)}"
        )
        console.print(f"Successful recoveries: {stats.get('successful_recoveries', 0)}")
        console.print(f"Failed recoveries: {stats.get('failed_recoveries', 0)}")
        console.print(f"Total files backed up: {stats.get('total_files_backed_up', 0)}")
        console.print(
            f"Total backup size: {stats.get('total_backup_size_mb', 0):.2f} MB"
        )

        from helpers.recovery import list_recent_operations

        recent_ops = list_recent_operations(7)
        if recent_ops:
            console.print("\nRecent operations (last 7 days):")
            for op in recent_ops[:10]:  # Show last 10
                console.print(
                    f"  {op['timestamp']}: {op['operation_type']} - {op['files_affected']} files"
                )
        else:
            console.print("\nNo recent operations found.")

    elif args.action == "stats":
        stats = get_recovery_stats()
        console.print("\n📊 Recovery System Statistics:")
        console.print(
            f"   Recoverable Operations: {stats.get('recoverable_operations', 0)}"
        )
        console.print(f"   Total Files: {stats.get('total_files_recoverable', 0):,}")
        console.print(
            f"   Total Size: {stats.get('total_size_recoverable', 0) / (1024**3):.2f} GB"
        )
        if stats.get("oldest_operation"):
            console.print(f"   Oldest Operation: {stats['oldest_operation']}")
        if stats.get("newest_operation"):
            console.print(f"   Newest Operation: {stats['newest_operation']}")
        if not stats.get("recoverable_operations", 0):
            console.print("   No recovery operations available.")

    elif args.action == "logs":
        from helpers.audit import get_audit_summary
        summary = get_audit_summary(24)  # Last 24 hours
        console.print("\n📋 Audit Log Summary (Last 24 Hours):")
        console.print(f"   Total Events: {summary.get('total_events', 0)}")
        console.print(f"   Scan Operations: {summary.get('scan_operations', 0)}")
        console.print(f"   Cleanup Operations: {summary.get('cleanup_operations', 0)}")
        console.print(f"   Security Events: {summary.get('security_events', 0)}")
        console.print(f"   Errors: {summary.get('errors', 0)}")
        if summary.get("session_id"):
            console.print(f"   Session ID: {summary['session_id']}")
        if summary.get("total_events", 0) == 0:
            console.print("   No audit events found in the last 24 hours.")

    elif args.action == "restore":
        if not args.operation_id:
            console.print("Error: --operation-id is required for restore action")
            return
        console.print(f"Restoring operation {args.operation_id} - not yet implemented")
        # TODO: Implement restore functionality


def handle_cache_command(args):
    """Handle the cache subcommand for system-wide cache management."""
    colors = get_terminal_colors()
    CYAN, MAGENTA, YELLOW, RESET, BOLD, BRIGHT_CYAN, BRIGHT_MAGENTA, GREEN, RED = colors[:9]

    console.print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}SYSTEM CACHE{CYAN}]{RESET} {YELLOW}Starting system cache cleanup...{RESET}")

    # Determine platform
    if args.platform == "auto":
        if sys.platform == "darwin":
            platform = "macos"
        elif sys.platform == "linux":
            platform = "linux"
        elif sys.platform == "win32":
            platform = "windows"
        else:
            console.print(f"{BOLD}{CYAN}[{RED}!{CYAN}]{RESET} {RED}Unsupported platform: {sys.platform}{RESET}")
            return
    else:
        platform = args.platform

    console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Target platform:{RESET} {BRIGHT_CYAN}{platform}{RESET}")

    # Get cache targets for the platform
    cache_targets = []
    config = get_config()

    try:
        if platform == "macos":
            from ..platforms.macos import get_macos_cache_targets
            cache_targets = get_macos_cache_targets(config.get("cache_targets", {}))
        elif platform == "linux":
            from ..platforms.linux import get_linux_cache_targets
            cache_targets = get_linux_cache_targets(config.get("cache_targets", {}))
        elif platform == "windows":
            from ..platforms.windows import get_windows_cache_targets
            cache_targets = get_windows_cache_targets(config.get("cache_targets", {}))
    except ImportError as e:
        console.print(f"{BOLD}{CYAN}[{RED}!{CYAN}]{RESET} {RED}Failed to load platform module: {e}{RESET}")
        return

    if not cache_targets:
        console.print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}No cache targets found for platform {platform}{RESET}")
        return

    # Filter targets if specific ones requested
    if args.targets:
        target_names = set(args.targets)
        cache_targets = [t for t in cache_targets if t.category in target_names]

    if not cache_targets:
        console.print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}No matching cache targets found{RESET}")
        return

    # Add Docker if requested
    if args.include_docker:
        from ..core.docker_integration import DockerIntegration
        docker = DockerIntegration()
        if docker.is_available():
            console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Docker integration enabled{RESET}")
        else:
            console.print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}Docker not available, skipping Docker cleanup{RESET}")

    # Display targets to be processed
    console.print(f"\n{BOLD}{CYAN}[{MAGENTA}TARGETS{CYAN}]{RESET} {YELLOW}Cache targets to process:{RESET}")
    safe_targets = [t for t in cache_targets if t.safety_level.name == "SAFE"]
    caution_targets = [t for t in cache_targets if t.safety_level.name == "CAUTION"]
    dangerous_targets = [t for t in cache_targets if t.safety_level.name == "DANGEROUS"]

    if safe_targets:
        console.print(f"{GREEN}Safe targets:{RESET}")
        for target in safe_targets:
            retention = f" ({target.retention_days}d retention)" if target.retention_days else ""
            console.print(f"  • {target.category}: {target.path}{retention}")

    if caution_targets:
        console.print(f"{YELLOW}Caution targets:{RESET}")
        for target in caution_targets:
            retention = f" ({target.retention_days}d retention)" if target.retention_days else ""
            console.print(f"  • {target.category}: {target.path}{retention}")

    if dangerous_targets:
        console.print(f"{RED}Dangerous targets:{RESET}")
        for target in dangerous_targets:
            retention = f" ({target.retention_days}d retention)" if target.retention_days else ""
            console.print(f"  • {target.category}: {target.path}{retention}")

    # Confirm operation
    if not args.force:
        total_targets = len(cache_targets)
        dangerous_count = len(dangerous_targets)

        if dangerous_count > 0:
            confirm_msg = f"This will process {total_targets} cache targets including {dangerous_count} dangerous operations. Continue? [y/N]: "
        else:
            confirm_msg = f"This will process {total_targets} cache targets. Continue? [y/N]: "

        if not input(f"\n{YELLOW}{confirm_msg}{RESET}").strip().lower().startswith("y"):
            console.print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}Cache cleanup cancelled.{RESET}")
            return

    # Perform cleanup
    console.print(f"\n{BOLD}{CYAN}[{MAGENTA}CLEANUP{CYAN}]{RESET} {YELLOW}Processing cache targets...{RESET}")

    from ..core.retention_policy import RetentionPolicyEngine
    security_config = get_typed_config().security
    engine = RetentionPolicyEngine(security_config.__dict__)

    operations = engine.apply_retention_policies(cache_targets, dry_run=args.dry_run, force=args.force)

    # Handle Docker cleanup if requested
    if args.include_docker:
        docker = DockerIntegration()
        if docker.is_available():
            console.print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}DOCKER{CYAN}]{RESET} {YELLOW}Processing Docker cleanup...{RESET}")

            # Estimate Docker cleanup size
            estimate = docker.estimate_cleanup_size()
            if estimate.get("estimated_mb", 0) > 0:
                console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Estimated Docker reclaimable space:{RESET} {BRIGHT_MAGENTA}{estimate['estimated_mb']:.1f} MB{RESET}")

                if not args.dry_run and not args.force:
                    if not input(f"{YELLOW}Proceed with Docker cleanup? [y/N]: {RESET}").strip().lower().startswith("y"):
                        console.print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}Docker cleanup skipped.{RESET}")
                    else:
                        docker_result = docker.perform_cleanup(volumes=False, dry_run=False, force=True)
                        if docker_result.get("success"):
                            console.print(f"{BOLD}{CYAN}[{GREEN}✓{CYAN}]{RESET} {GREEN}Docker cleanup completed{RESET}")
                        else:
                            console.print(f"{BOLD}{CYAN}[{RED}!{CYAN}]{RESET} {RED}Docker cleanup failed: {docker_result.get('error', 'Unknown error')}{RESET}")
                elif args.dry_run:
                    docker_result = docker.perform_cleanup(volumes=False, dry_run=True, force=True)
                    console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Docker dry-run completed{RESET}")
            else:
                console.print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}No Docker cleanup needed{RESET}")

    # Display results
    summary = engine.get_cleanup_summary(operations)

    console.print(f"\n{BOLD}{CYAN}[{MAGENTA}RESULTS{CYAN}]{RESET} {YELLOW}Cleanup Summary:{RESET}")
    console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Operations processed:{RESET} {BRIGHT_CYAN}{summary['total_operations']}{RESET}")
    console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Successful operations:{RESET} {GREEN}{summary['successful_operations']}{RESET}")
    console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Skipped operations:{RESET} {YELLOW}{summary['skipped_operations']}{RESET}")
    console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Failed operations:{RESET} {RED}{summary['failed_operations']}{RESET}")
    console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Total space reclaimed:{RESET} {BRIGHT_MAGENTA}{summary['total_size_mb']:.1f} MB{RESET}")
    console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Files processed:{RESET} {BRIGHT_CYAN}{summary['total_files_deleted']}{RESET}")

    if summary['failed_operations'] > 0:
        console.print(f"\n{BOLD}{CYAN}[{RED}ERRORS{CYAN}]{RESET} {RED}Some operations failed:{RESET}")
        for op in summary['operations']:
            if op['result'] == 'failed':
                console.print(f"  • {op['target']}: {op['error_message']}")

    if args.dry_run:
        console.print(f"\n{BOLD}{CYAN}[{YELLOW}DRY RUN{CYAN}]{RESET} {YELLOW}This was a dry run - no files were actually deleted{RESET}")
    else:
        console.print(f"\n{BOLD}{CYAN}[{GREEN}✓{CYAN}]{RESET} {GREEN}System cache cleanup completed{RESET}")

    logger.info(
        "System cache cleanup completed",
        extra={
            "platform": platform,
            "dry_run": args.dry_run,
            "total_operations": summary['total_operations'],
            "successful_operations": summary['successful_operations'],
            "total_size_mb": summary['total_size_mb'],
            "total_files": summary['total_files_deleted'],
        },
    )


def handle_config_command(args):
    """Handle the config subcommand."""
    import json

    try:
        if args.action == "get":
            if not args.key:
                console.print("Error: key is required for get action")
                return

            config = get_config()
            value = get_setting(args.key)
            if value is not None:
                if isinstance(value, (list, dict)):
                    console.print(json.dumps(value, indent=2))
                else:
                    console.print(value)
            else:
                console.print(f"Key '{args.key}' not found")

        elif args.action == "set":
            if not args.key or args.value is None:
                console.print("Error: key and value are required for set action")
                return

            # Try to parse value as JSON first, then as literal
            value = args.value
            try:
                value = json.loads(args.value)
            except (json.JSONDecodeError, ValueError):
                # Try to convert to appropriate type
                if args.value.lower() in ("true", "false"):
                    value = args.value.lower() == "true"
                elif args.value.isdigit():
                    value = int(args.value)
                elif args.value.replace(".", "").isdigit():
                    try:
                        value = float(args.value)
                    except ValueError:
                        pass  # Keep as string

            update_config(args.key, value, save=True)
            console.print(f"Set {args.key} = {value}")

        elif args.action == "list":
            config = get_typed_config()
            console.print("=== LazyScan Configuration ===")
            console.print(f"Config file: {get_config_info()['config_file']}")
            console.print()

            console.print("[general]")
            for key, value in config.general.__dict__.items():
                console.print(f"  {key} = {value}")
            console.print()

            console.print("[scan]")
            for key, value in config.scan.__dict__.items():
                console.print(f"  {key} = {value}")
            console.print()

            console.print("[unity]")
            for key, value in config.unity.__dict__.items():
                console.print(f"  {key} = {value}")
            console.print()

            console.print("[security]")
            for key, value in config.security.__dict__.items():
                console.print(f"  {key} = {value}")

        elif args.action == "reset":
            reset_config()
            console.print("Configuration reset to defaults")

        elif args.action == "info":
            info = get_config_info()
            console.print("=== Configuration System Info ===")
            for key, value in info.items():
                console.print(f"{key}: {value}")

    except Exception as e:
        console.print(f"Error: {e}")
        logger.error(f"Config command failed: {e}", exc_info=True)


def handle_application_specific_scans_legacy(args, colors):
    """Legacy handler for application-specific scans in scan command."""
    app_scan_requested = any([
        args.firefox,
        args.vscode,
    ])

    if not app_scan_requested:
        return False

    logger.info(
        "Starting application-specific cache scans",
        extra={
            "requested_apps": [
                app for app in ["firefox", "vscode"]
                if getattr(args, app, False)
            ]
        },
    )

    if args.firefox:
        scan_application_cache(
            "Firefox",
            FIREFOX_PATHS,
            colors,
            check_path="~/.mozilla/firefox" if sys.platform != "darwin" else "~/Library/Application Support/Firefox",
        )

    if args.vscode:
        scan_application_cache(
            "VS Code",
            VSCODE_PATHS,
            colors,
            check_path="~/.vscode" if sys.platform != "darwin" else "~/Library/Application Support/Code",
        )

    return True


def handle_security_and_recovery_commands(args):
    """Handle security and recovery related commands."""
    if args.recovery:
        console.print("\n=== Recovery System ===")
        stats = get_recovery_stats()
        console.print(
            f"Total recoverable operations: {stats.get('total_operations', 0)}"
        )
        console.print(f"Successful recoveries: {stats.get('successful_recoveries', 0)}")
        console.print(f"Failed recoveries: {stats.get('failed_recoveries', 0)}")
        console.print(f"Total files backed up: {stats.get('total_files_backed_up', 0)}")
        console.print(
            f"Total backup size: {stats.get('total_backup_size_mb', 0):.2f} MB"
        )

        from helpers.recovery import list_recent_operations

        recent_ops = list_recent_operations(7)
        if recent_ops:
            console.print("\nRecent operations (last 7 days):")
            for op in recent_ops[:10]:  # Show last 10
                console.print(
                    f"  {op['timestamp']}: {op['operation_type']} - {op['files_affected']} files"
                )
        else:
            console.print("\nNo recent operations found.")
        return True

    if args.audit_logs:
        from helpers.audit import get_audit_summary
        summary = get_audit_summary(24)  # Last 24 hours
        console.print("\n📋 Audit Log Summary (Last 24 Hours):")
        console.print(f"   Total Events: {summary.get('total_events', 0)}")
        console.print(f"   Scan Operations: {summary.get('scan_operations', 0)}")
        console.print(f"   Cleanup Operations: {summary.get('cleanup_operations', 0)}")
        console.print(f"   Security Events: {summary.get('security_events', 0)}")
        console.print(f"   Errors: {summary.get('errors', 0)}")
        if summary.get("session_id"):
            console.print(f"   Session ID: {summary['session_id']}")
        if summary.get("total_events", 0) == 0:
            console.print("   No audit events found in the last 24 hours.")
        return True

    if args.recovery_stats:
        stats = get_recovery_stats()
        console.print("\n📊 Recovery System Statistics:")
        console.print(
            f"   Recoverable Operations: {stats.get('recoverable_operations', 0)}"
        )
        console.print(f"   Total Files: {stats.get('total_files_recoverable', 0):,}")
        console.print(
            f"   Total Size: {stats.get('total_size_recoverable', 0) / (1024**3):.2f} GB"
        )
        if stats.get("oldest_operation"):
            console.print(f"   Oldest Operation: {stats['oldest_operation']}")
        if stats.get("newest_operation"):
            console.print(f"   Newest Operation: {stats['newest_operation']}")
        if not stats.get("recoverable_operations", 0):
            console.print("   No recovery operations available.")
        return True

    return False


def handle_application_specific_scans(args, colors):
    """Handle application-specific cache scans."""
    app_scan_requested = any(
        [
            args.perplexity,
            args.dia,
            args.slack,
            args.discord,
            args.spotify,
            args.vscode,
            args.zoom,
            args.teams,
            args.firefox,
            args.safari,
        ]
    )

    if not app_scan_requested:
        return False

    logger.info(
        "Starting application-specific cache scans",
        extra={
            "requested_apps": [
                app
                for app in [
                    "perplexity",
                    "dia",
                    "slack",
                    "discord",
                    "spotify",
                    "vscode",
                    "zoom",
                    "teams",
                    "firefox",
                    "safari",
                ]
                if getattr(args, app, False)
            ]
        },
    )

    # Handle each application - use generic scanning for now (dedicated modules need fixes)
    if args.firefox:
        scan_application_cache(
            "Firefox",
            FIREFOX_PATHS,
            colors,
            check_path="~/.mozilla/firefox" if sys.platform != "darwin" else "~/Library/Application Support/Firefox",
        )

    if args.vscode:
        scan_application_cache(
            "VS Code",
            VSCODE_PATHS,
            colors,
            check_path="~/.vscode" if sys.platform != "darwin" else "~/Library/Application Support/Code",
        )

    # Generic cache scanning for simpler applications
    if args.perplexity:
        scan_application_cache(
            "Perplexity",
            PERPLEXITY_PATHS,
            colors,
            check_path="~/.config/perplexity" if sys.platform != "darwin" else "~/Library/Application Support/Perplexity",
        )

    if args.dia:
        scan_application_cache(
            "Dia", DIA_PATHS, colors, check_path="~/.local/share/dia" if sys.platform != "darwin" else "~/Library/Application Support/Dia"
        )

    if args.slack:
        scan_application_cache(
            "Slack",
            SLACK_PATHS,
            colors,
            check_path="~/.config/Slack" if sys.platform != "darwin" else "~/Library/Application Support/Slack",
        )

    if args.discord:
        scan_application_cache(
            "Discord",
            DISCORD_PATHS,
            colors,
            check_path="~/.config/discord" if sys.platform != "darwin" else "~/Library/Application Support/discord",
        )

    if args.spotify:
        scan_application_cache(
            "Spotify",
            SPOTIFY_PATHS,
            colors,
            check_path="~/.cache/spotify" if sys.platform != "darwin" else "~/Library/Application Support/Spotify",
        )

    if args.zoom:
        scan_application_cache(
            "Zoom",
            ZOOM_PATHS,
            colors,
            check_path="~/.zoom" if sys.platform != "darwin" else "~/Library/Application Support/zoom.us",
        )

    if args.teams:
        scan_application_cache(
            "Teams",
            TEAMS_PATHS,
            colors,
            check_path="~/.config/teams" if sys.platform != "darwin" else "~/Library/Application Support/Microsoft/Teams",
        )

    if args.safari:
        if sys.platform == "darwin":
            scan_application_cache(
                "Safari",
                SAFARI_PATHS,
                colors,
                check_path="~/Library/Caches/com.apple.Safari",
            )
        else:
            console.print("\n⚠️  Safari is only available on macOS.")

    return True


def handle_macos_cache_cleaning(args):
    """Handle macOS system cache cleaning."""
    if not args.macos:
        return False

    # Platform guard - macOS only feature
    if sys.platform != "darwin":
        logger.error(
            "macOS cache cleaning attempted on non-macOS platform",
            extra={"platform": sys.platform},
        )
        console.print("\nError: --macos option is only available on macOS.")
        sys.exit(1)

    logger.info(
        "Starting macOS cache cleaning", extra={"operation": "macos_cache_clean"}
    )

    # Get disk usage before cleaning
    total_before, used_before, free_before, _ = get_system_disk_usage("/")

    # Setup colors for cache cleaning
    colors = get_terminal_colors()

    # Display initial disk usage
    console.print(
        f"\n{colors[4]}{colors[0]}[{colors[5]}SYSTEM STATUS{colors[0]}]{colors[3]} {colors[2]}Current disk usage:{colors[3]}"
    )
    _, _, _, usage_before_str = get_system_disk_usage("/")
    console.print(usage_before_str)

    # Clean macOS cache directories
    freed_bytes = clean_macos_cache(SYSTEM_CACHE_PATHS, colors)

    # Get disk usage after cleaning
    total_after, used_after, free_after, _ = get_system_disk_usage("/")

    # Display summary banner if space was actually freed
    if freed_bytes > 0:
        display_cache_cleanup_summary(
            freed_bytes,
            used_before,
            used_after,
            total_before,
            total_after,
            free_before,
            free_after,
            colors,
        )

        # Display updated disk usage
        console.print(
            f"\n{colors[4]}{colors[0]}[{colors[5]}SYSTEM STATUS{colors[0]}]{colors[3]} {colors[2]}Updated disk usage:{colors[3]}"
        )
        _, _, _, usage_after_str = get_system_disk_usage("/")
        console.print(usage_after_str)

    logger.info(
        "macOS cache cleaning completed",
        extra={
            "freed_bytes": freed_bytes,
            "used_before": used_before,
            "used_after": used_after,
        },
    )

    return True


@cli_error_handler
def main():
    """Main entry point for LazyScan."""
    parser = create_argument_parser()
    args = parser.parse_args()

    # Configure logging system with human-readable format
    setup_development_logging(verbose=False)

    logger.info("LazyScan starting", extra={"version": __version__, "command": args.command, "args": vars(args)})

    # Show logo and disclaimer (except for recovery command)
    if not getattr(args, 'no_logo', False) and args.command != "recovery":
        show_logo()
        # Check and display disclaimer only if not acknowledged and not skipped
        if not has_seen_disclaimer() and not getattr(args, 'no_disclaimer', False):
            show_disclaimer()
            input("Press Enter to acknowledge the disclaimer and continue...")
            mark_disclaimer_acknowledged()

    # Initialize security system
    security_enabled = initialize_security_system()

    try:
        # Dispatch to command handlers
        if args.command == "scan":
            handle_scan_command(args)
        elif args.command == "clean":
            handle_clean_command(args)
        elif args.command == "recovery":
            handle_recovery_command(args)
        elif args.command == "config":
            handle_config_command(args)
        elif args.command == "cache":
            handle_cache_command(args)
        else:
            parser.error(f"Unknown command: {args.command}")

    finally:
        # Properly shutdown security system
        try:
            if security_enabled:
                audit_logger.log_shutdown({"clean_exit": True})
                logger.info("Security system shutdown completed")
        except Exception as e:
            logger.warning("Security system shutdown failed", extra={"error": str(e)})
            pass  # Don't let shutdown errors affect the main program


@cli_error_handler
def cli_main():
    """Entry point for the CLI when installed as a package."""
    main()


if __name__ == "__main__":
    cli_main()
