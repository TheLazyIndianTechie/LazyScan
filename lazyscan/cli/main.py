#!/usr/bin/env python3
"""
Main CLI module for LazyScan.
Handles argument parsing, main execution flow, and coordination between modules.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import List, Optional

import typer
import orjson
import humanfriendly

# Create Typer app
app = typer.Typer(
    name="lazyscan",
    help="A lazy way to find what's eating your disk space",
    add_completion=False,
)

from ..core.logging_config import (
    get_logger, get_console, setup_development_logging,
    log_cleanup_operation, log_scan_operation, log_operation
)
from ..core.formatting import human_readable, get_terminal_colors, ProgressDisplay, parse_size


def validate_min_size(value: str) -> str:
    """Validate and normalize min-size parameter with cyberpunk flair."""
    if not value or value.strip() == "":
        return "0B"

    value = value.strip()
    if value.upper() == "0B":
        return "0B"

    try:
        # Use humanfriendly directly for robust parsing
        parsed_bytes = humanfriendly.parse_size(value)
        if parsed_bytes < 0:
            raise typer.BadParameter("🛑 NEURAL LINK ERROR: Size cannot be negative, choom. Try something positive.")
        if parsed_bytes > 10**15:  # 1 PB limit
            raise typer.BadParameter("🚫 MATRIX OVERLOAD: Size too massive! Max 1PB allowed.")
        return value
    except humanfriendly.InvalidSize as e:
        raise typer.BadParameter(f"🛑 CYBERDECK MALFUNCTION: Invalid size format '{value}'. Use formats like '1MB', '500KB', '2.5GB'. Error: {e}")
    except Exception as e:
        raise typer.BadParameter(f"🛑 SYSTEM CRASH: Size parsing failed for '{value}': {e}")


def validate_exclude_pattern(pattern: str) -> str:
    """Validate exclude pattern with enhanced glob checking."""
    if not pattern or pattern.strip() == "":
        raise typer.BadParameter("🛑 VOID PATTERN: Exclude pattern cannot be empty, runner.")

    pattern = pattern.strip()

    # Check for dangerous patterns
    dangerous_patterns = ["**", "/*", "/**", "~/", "~/**"]
    for dangerous in dangerous_patterns:
        if pattern.startswith(dangerous):
            raise typer.BadParameter(f"🚫 SECURITY BREACH: Dangerous exclude pattern '{pattern}' detected. Avoid absolute paths and root patterns.")

    # Check for obviously invalid glob patterns
    invalid_chars = ["<", ">", "|", "&", ";"]
    for char in invalid_chars:
        if char in pattern:
            raise typer.BadParameter(f"🛑 MALICIOUS CODE: Invalid character '{char}' in exclude pattern '{pattern}'.")

    # Basic length check
    if len(pattern) > 256:
        raise typer.BadParameter("🚫 PATTERN OVERFLOW: Exclude pattern too long (max 256 chars).")

    return pattern


def validate_top_count(value: int) -> int:
    """Validate top file count with performance considerations."""
    if value < 1:
        raise typer.BadParameter("🛑 NEGATIVE VOID: Top count must be at least 1, choom.")
    if value > 10000:
        raise typer.BadParameter("🚫 MATRIX OVERLOAD: Top count cannot exceed 10,000. That's too many files to display!")
    if value > 1000:
        # Warning for large values
        typer.echo(f"⚠️  HIGH LOAD WARNING: Top count of {value} may slow down scanning. Consider values under 1000.")

    return value
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
)
from ..core.scanner import get_system_disk_usage, scan_directory_with_progress
from ..core.scan import scan_directory, scan_directory_sync
from ..core.serialization import serialize_scan_result, scan_result_to_dict, serialize_cleanup_summary
from ..apps.unity import handle_unity_discovery
from ..apps.unreal import handle_unreal_discovery
from ..apps.chrome import handle_chrome_discovery

# Import security framework
from helpers.audit import audit_logger
from helpers.secure_operations import configure_security
from helpers.recovery import get_recovery_stats, register_operation_for_recovery


logger = get_logger(__name__)
console = get_console()
__version__ = "0.6.4"

# Initialize Sentry for error tracking (must be done after version is defined)
try:
    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration

    # Only initialize if DSN is provided
    sentry_dsn = os.getenv("SENTRY_DSN")
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            # Add data like request headers and IP for users
            send_default_pii=True,
            # Set traces sample rate to 1.0 to capture 100% of transactions for performance monitoring
            traces_sample_rate=1.0,
            # Enable logging integration
            integrations=[
                LoggingIntegration(
                    level=None,  # Capture all log levels
                    event_level=None  # Send all log levels as events
                ),
            ],
            # Release tracking
            release=f"lazyscan@{__version__}",
            # Environment
            environment=os.getenv("SENTRY_ENVIRONMENT", "production"),
            # Sample rate for error events
            sample_rate=1.0,
        )
        sentry_enabled = True
    else:
        sentry_enabled = False
except ImportError:
    sentry_enabled = False

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


# Global options
no_disclaimer: bool = typer.Option(False, "--no-disclaimer", help="skip disclaimer acknowledgment (for automation)")


@app.callback()
def main_callback(
    version: bool = typer.Option(False, "--version", help="show version number and exit"),
    no_disclaimer: bool = no_disclaimer,
):
    """A lazy way to find what's eating your disk space."""
    if version:
        typer.echo(f"lazyscan {__version__}")
        raise typer.Exit()


@app.command("scan")
def scan_command(
    path: Optional[Path] = typer.Argument(None, help="directory path to scan (default: current directory)"),
    top: int = typer.Option(get_scanning_setting("top_files", 20), "-n", "--top", help=f"number of top files to display (default: {get_scanning_setting('top_files', 20)})", callback=validate_top_count),
    width: int = typer.Option(get_ui_setting("bar_width", 40), "-w", "--width", help=f"bar width in characters (default: {get_ui_setting('bar_width', 40)})"),
    interactive: bool = typer.Option(False, "-i", "--interactive", help="prompt to choose directory (for the truly lazy)"),
    no_logo: bool = typer.Option(False, "--no-logo", help="hide the lazyscan logo"),
    json_output: bool = typer.Option(False, "--json", help="output scan results in machine-readable JSON format (bypasses UI chrome)"),
    exclude: List[str] = typer.Option([], "--exclude", help="glob patterns to exclude from scan (supports wildcards, can be used multiple times)", callback=validate_exclude_pattern),
    min_size: str = typer.Option("0B", "--min-size", help="minimum file size filter (e.g., '1MB', '500KB', '2GB', '100K') - keeps only bigger targets", callback=validate_min_size),
    # Application-specific options
    chrome: bool = typer.Option(False, "--chrome", help="scan Chrome Application Support for cleanable files"),
    unity: bool = typer.Option(False, "--unity", help="scan Unity projects and cache"),
    unreal: bool = typer.Option(False, "--unreal", help="scan Unreal Engine projects"),
    firefox: bool = typer.Option(False, "--firefox", help="scan Firefox cache for cleanable files"),
    vscode: bool = typer.Option(False, "--vscode", help="scan VS Code cache for cleanable files"),
):
    """Scan directories and files for disk usage analysis."""
    # In JSON mode, suppress all decorative output
    if not json_output:
        show_logo_and_disclaimer_if_needed(no_logo)

    # Create args object for compatibility with existing functions
    class Args:
        def __init__(self):
            self.path = str(path) if path else None
            self.top = top
            self.width = width
            self.interactive = interactive
            self.no_logo = no_logo or json_output  # Always hide logo in JSON mode
            self.json = json_output
            self.exclude = exclude
            self.min_size = min_size
            self.chrome = chrome
            self.unity = unity
            self.unreal = unreal
            self.firefox = firefox
            self.vscode = vscode

    args = Args()
    handle_scan_command(args)


@app.command("clean")
def clean_command(
    target: str = typer.Argument(..., help="what to clean"),
    dry_run: bool = typer.Option(False, "--dry-run", help="show what would be cleaned without actually deleting"),
    force: bool = typer.Option(False, "--force", help="skip confirmation prompts (dangerous)"),
    permanent: bool = typer.Option(False, "--permanent", help="permanently delete instead of moving to trash"),
):
    """Clean cache directories and temporary files."""
    # Validate target
    valid_targets = ["macos", "unity", "chrome", "firefox", "vscode", "all"]
    if target not in valid_targets:
        typer.echo(f"Error: Invalid target '{target}'. Valid targets: {', '.join(valid_targets)}")
        raise typer.Exit(1)

    # Create args object for compatibility
    class Args:
        def __init__(self):
            self.target = target
            self.dry_run = dry_run
            self.force = force
            self.permanent = permanent

    args = Args()
    handle_clean_command(args)


@app.command("recovery")
def recovery_command(
    action: str = typer.Argument("list", help="recovery action to perform"),
    operation_id: Optional[str] = typer.Option(None, "--operation-id", help="specific operation ID to restore"),
):
    """Manage file recovery and audit logs."""
    valid_actions = ["list", "restore", "stats", "logs"]
    if action not in valid_actions:
        typer.echo(f"Error: Invalid action '{action}'. Valid actions: {', '.join(valid_actions)}")
        raise typer.Exit(1)

    # Create args object for compatibility
    class Args:
        def __init__(self):
            self.action = action
            self.operation_id = operation_id

    args = Args()
    handle_recovery_command(args)


@app.command("config")
def config_command(
    action: str = typer.Argument(..., help="configuration action to perform"),
    key: Optional[str] = typer.Argument(None, help="configuration key (for get/set actions)"),
    value: Optional[str] = typer.Argument(None, help="configuration value (for set action)"),
    app: Optional[str] = typer.Option(None, "--app", help="application-specific configuration (for per-app overrides)"),
):
    """Manage LazyScan configuration."""
    from ..core.config import get_setting, update_config, reset_config, get_typed_config, get_config_info

    valid_actions = ["get", "set", "list", "reset", "info"]
    if action not in valid_actions:
        typer.echo(f"Error: Invalid action '{action}'. Valid actions: {', '.join(valid_actions)}")
        raise typer.Exit(1)

    try:
        if action == "get":
            if not key:
                typer.echo("Error: key is required for get action")
                raise typer.Exit(1)

            config_value = get_setting(key)
            if config_value is not None:
                if isinstance(config_value, (list, dict)):
                    import json
                    typer.echo(json.dumps(config_value, indent=2))
                else:
                    typer.echo(config_value)
            else:
                typer.echo(f"Key '{key}' not found")

        elif action == "set":
            if not key or value is None:
                typer.echo("Error: key and value are required for set action")
                raise typer.Exit(1)

            # Try to parse value as JSON first, then as literal
            parsed_value = value
            try:
                import json
                parsed_value = json.loads(value)
            except (json.JSONDecodeError, ValueError):
                # Try to convert to appropriate type
                if value.lower() in ("true", "false"):
                    parsed_value = value.lower() == "true"
                elif value.isdigit():
                    parsed_value = int(value)
                elif value.replace(".", "").isdigit():
                    try:
                        parsed_value = float(value)
                    except ValueError:
                        pass  # Keep as string

            update_config(key, parsed_value, save=True)
            typer.echo(f"Set {key} = {parsed_value}")

        elif action == "list":
            config = get_typed_config()
            typer.echo("=== LazyScan Configuration ===")
            typer.echo(f"Config file: {get_config_info()['config_file']}")
            typer.echo()

            typer.echo("[general]")
            for k, v in config.general.__dict__.items():
                typer.echo(f"  {k} = {v}")
            typer.echo()

            typer.echo("[scan]")
            for k, v in config.scan.__dict__.items():
                typer.echo(f"  {k} = {v}")
            typer.echo()

            typer.echo("[unity]")
            for k, v in config.unity.__dict__.items():
                typer.echo(f"  {k} = {v}")
            typer.echo()

            typer.echo("[security]")
            for k, v in config.security.__dict__.items():
                typer.echo(f"  {k} = {v}")

        elif action == "reset":
            reset_config()
            typer.echo("Configuration reset to defaults")

        elif action == "info":
            info = get_config_info()
            typer.echo("=== Configuration System Info ===")
            for k, v in info.items():
                typer.echo(f"{k}: {v}")

    except Exception as e:
        typer.echo(f"Error: {e}")
        logger.error(f"Config command failed: {e}", exc_info=True)
        raise typer.Exit(1)


@app.command("migrate-audit")
def migrate_audit_command(
    action: str = typer.Argument(..., help="migration action to perform"),
    force: bool = typer.Option(False, "--force", help="skip confirmation prompts"),
    dry_run: bool = typer.Option(False, "--dry-run", help="show what would be migrated without actually doing it"),
):
    """Manage audit log encryption migration."""
    from lazyscan.security.audit_encryption_schema import AuditEncryptionConfig, AuditCompatibilityConfig
    from lazyscan.security.audit_migration import (
        AuditMigrationManager,
        detect_migration_needed,
        MigrationStatus
    )

    valid_actions = ["detect", "plan", "execute", "rollback", "status"]
    if action not in valid_actions:
        typer.echo(f"Error: Invalid action '{action}'. Valid actions: {', '.join(valid_actions)}")
        raise typer.Exit(1)

    try:
        # Initialize migration manager
        encryption_config = AuditEncryptionConfig()
        compatibility_config = AuditCompatibilityConfig()
        manager = AuditMigrationManager(encryption_config, compatibility_config)

        if action == "detect":
            # Detect if migration is needed
            console.print("🔍 Detecting plaintext audit directories...")

            migration_needed, results = detect_migration_needed()

            if migration_needed:
                console.print("✅ Migration needed!")
                console.print(f"   Platforms requiring migration: {len(results['directories'])}")

                for dir_info in results["directories"]:
                    console.print(f"   • {dir_info['platform']}: {len(dir_info['plaintext_files'])} plaintext files")
            else:
                console.print("ℹ️  No migration needed - all audit logs are encrypted")

            # Show detailed results
            console.print("\n📊 Detection Results:")
            for dir_info in results["directories"]:
                console.print(f"   {dir_info['platform'].title()}:")
                console.print(f"     Path: {dir_info['path']}")
                console.print(f"     Exists: {dir_info['exists']}")
                console.print(f"     Plaintext files: {len(dir_info['plaintext_files'])}")
                console.print(f"     Encrypted files: {len(dir_info['encrypted_files'])}")
                console.print(f"     Mixed state: {dir_info['mixed_state']}")

        elif action == "plan":
            # Plan the migration
            console.print("📋 Planning audit log migration...")

            directories = manager.detect_plaintext_directories()
            plan = manager.plan_migration(directories)

            if not plan["requires_migration"]:
                console.print("ℹ️  No migration needed")
                return

            console.print("📝 Migration Plan:")
            console.print(f"   Migration ID: {plan['migration_id']}")
            console.print(f"   Total plaintext files: {plan['total_plaintext_files']}")
            console.print(f"   Total encrypted files: {plan['total_encrypted_files']}")
            console.print(f"   Estimated duration: {plan['estimated_duration_minutes']} minutes")

            console.print("\n📂 Directories to migrate:")
            for dir_info in plan["directories"]:
                console.print(f"   • {dir_info['platform']}: {len(dir_info['plaintext_files'])} files")

            if not force and not dry_run:
                if not typer.confirm("Proceed with migration planning?"):
                    console.print("❌ Migration planning cancelled")
                    return

            # Create initial checkpoint
            checkpoint = manager.start_migration(plan)
            console.print(f"✅ Migration checkpoint created: {checkpoint.migration_id}")

        elif action == "execute":
            # Execute the migration
            console.print("🚀 Executing audit log migration...")

            if not force and not dry_run:
                console.print("⚠️  This will encrypt all plaintext audit logs")
                console.print("   Backups will be created for rollback purposes")
                if not typer.confirm("Continue with migration execution?"):
                    console.print("❌ Migration execution cancelled")
                    return

            # Find the latest migration checkpoint
            checkpoint_dir = manager.checkpoint_dir
            checkpoints = list(checkpoint_dir.glob("*.json"))

            if not checkpoints:
                console.print("❌ No migration checkpoints found. Run 'migrate-audit plan' first")
                return

            # Load the most recent checkpoint
            latest_checkpoint = max(checkpoints, key=lambda p: p.stat().st_mtime)
            checkpoint = manager.load_checkpoint(latest_checkpoint.stem)

            if not checkpoint:
                console.print("❌ Failed to load migration checkpoint")
                return

            if checkpoint.status == MigrationStatus.COMPLETED.value:
                console.print("ℹ️  Migration already completed")
                return

            console.print(f"📂 Resuming migration: {checkpoint.migration_id}")

            # Execute migration for each directory
            directories = manager.detect_plaintext_directories()
            success_count = 0

            for dir_info in directories:
                if dir_info.needs_migration():
                    console.print(f"   Migrating {dir_info.platform}...")

                    if not dry_run:
                        success = manager.migrate_directory(dir_info, checkpoint)
                        if success:
                            success_count += 1
                            console.print(f"   ✅ {dir_info.platform} migration completed")
                        else:
                            console.print(f"   ❌ {dir_info.platform} migration failed")
                    else:
                        console.print(f"   [DRY RUN] Would migrate {len(dir_info.plaintext_files)} files in {dir_info.platform}")
                        success_count += 1

            if success_count == len([d for d in directories if d.needs_migration()]):
                console.print("🎉 Migration completed successfully!")
            else:
                console.print("⚠️  Migration completed with errors")

        elif action == "rollback":
            # Rollback a failed migration
            console.print("🔄 Rolling back audit log migration...")

            if not force and not dry_run:
                console.print("⚠️  This will restore plaintext logs from backups")
                if not typer.confirm("Continue with rollback?"):
                    console.print("❌ Rollback cancelled")
                    return

            # Find migration checkpoints
            checkpoint_dir = manager.checkpoint_dir
            checkpoints = list(checkpoint_dir.glob("*.json"))

            if not checkpoints:
                console.print("❌ No migration checkpoints found")
                return

            # Load the most recent checkpoint
            latest_checkpoint = max(checkpoints, key=lambda p: p.stat().st_mtime)
            checkpoint = manager.load_checkpoint(latest_checkpoint.stem)

            if not checkpoint:
                console.print("❌ Failed to load migration checkpoint")
                return

            console.print(f"🔄 Rolling back migration: {checkpoint.migration_id}")

            if not dry_run:
                success = manager.rollback_migration(checkpoint)
                if success:
                    console.print("✅ Rollback completed successfully")
                else:
                    console.print("❌ Rollback failed")
            else:
                console.print("   [DRY RUN] Would rollback migration")

        elif action == "status":
            # Show migration status
            console.print("📊 Migration Status:")

            checkpoint_dir = manager.checkpoint_dir
            checkpoints = list(checkpoint_dir.glob("*.json"))

            if not checkpoints:
                console.print("   No migration checkpoints found")
                return

            # Show all checkpoints
            for checkpoint_file in sorted(checkpoints, key=lambda p: p.stat().st_mtime, reverse=True):
                checkpoint = manager.load_checkpoint(checkpoint_file.stem)
                if checkpoint:
                    console.print(f"\n📋 Migration: {checkpoint.migration_id}")
                    console.print(f"   Status: {checkpoint.status}")
                    console.print(f"   Phase: {checkpoint.phase}")
                    console.print(f"   Files processed: {len(checkpoint.processed_files)}")
                    console.print(f"   Files failed: {len(checkpoint.failed_files)}")
                    console.print(f"   Started: {checkpoint.start_time}")
                    console.print(f"   Last update: {checkpoint.last_update}")

                    if checkpoint.metadata.get("failure_reason"):
                        console.print(f"   Failure reason: {checkpoint.metadata['failure_reason']}")

    except Exception as e:
        console.print(f"❌ Migration command failed: {e}")
        logger.error(f"Migration command failed: {e}", exc_info=True)
        raise typer.Exit(1)





def apply_filters(file_sizes: list, exclude_patterns: Optional[list] = None, min_size_str: Optional[str] = None) -> list:
    """Apply filtering to file sizes list.

    Note: Size filtering is now handled in the scan pipeline.
    This function is kept for backward compatibility and additional filtering if needed.
    """
    import fnmatch
    import os

    filtered = file_sizes.copy()

    # Size filtering is now done in scan_directory() - no need to do it here

    # Apply exclude patterns (additional filtering if needed)
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
        # Use async scanning with progress callback (only if not JSON mode)
        progress_display = None
        progress_callback = None

        if not args.json:
            # Only show progress UI when not in JSON mode
            progress_display = ProgressDisplay()

            async def progress_callback(path: Path, data: dict) -> None:
                """Async progress callback that updates the terminal display."""
                if isinstance(data, dict) and 'files_processed' in data:
                    # Directory progress update
                    rel_path = os.path.relpath(str(path), scan_path)
                    rel_path = "." if rel_path == "." else f".../{rel_path}"
                    progress_display.update_progress(
                        "Scanning",
                        data.get('files_processed', 0),
                        data.get('total_files', 0) or 1,  # Avoid division by zero
                        extra_info=rel_path
                    )

        # Parse minimum size filter
        min_size_bytes = 0
        if args.min_size:
            try:
                min_size_bytes = parse_size(args.min_size)
            except ValueError as e:
                if not args.json:
                    console.print(f"Warning: Invalid min-size format '{args.min_size}': {e}")
                    console.print("Ignoring min-size filter.")

        # Run scan using synchronous wrapper for backward compatibility
        scan_result = scan_directory_sync(
            Path(scan_path),
            max_depth=None,  # TODO: Add max_depth support from args
            exclude_patterns=args.exclude,
            min_size_bytes=min_size_bytes,
            progress_callback=progress_callback
        )

        # Complete progress display (only if not JSON mode)
        if progress_display is not None:
            progress_display.finish_progress("Scan completed")

        # Convert result format to match existing code expectations
        file_sizes = scan_result['files']

        if not file_sizes:
            console.print(f"No files found under '{scan_path}'.")
            logger.warning(
                "No files found in scan path", extra={"scan_path": scan_path}
            )
            return

        # Apply additional filters (size filtering already done in scan pipeline)
        filtered_files = apply_filters(file_sizes, args.exclude, None)

        if not filtered_files:
            console.print("No files match the specified filters.")
            return

        # Sort and select top N files
        filtered_files.sort(key=lambda x: x[1], reverse=True)
        top_files = filtered_files[: args.top]
        total_size = sum(size for _, size in top_files)

        if args.json:
            # JSON output mode - clean output without ASCII art or other UI elements
            # Create a proper ScanResult-like structure for serialization
            from ..core.scan import ScanResult
            import time

            # Reconstruct ScanResult from the scan data
            reconstructed_result = ScanResult(
                total_size=scan_result['total_size'],
                file_count=scan_result['file_count'],
                dir_count=scan_result['dir_count'],
                files=top_files,  # Only include top files for JSON output
                errors=scan_result['errors'],
                scan_duration=0.0,  # Not available in sync wrapper
                metadata={
                    "scan_path": scan_path,
                    "top_files_count": len(top_files),
                    "filtered_total": len(filtered_files),
                    "timestamp": time.time()
                }
            )

            # Use the serialization utility
            json_bytes = serialize_scan_result(reconstructed_result)
            typer.echo(json_bytes.decode('utf-8'))
        else:
            # Display results with full UI
            display_scan_results_header(len(top_files), colors)

            # Render results table
            from ..core.formatting import render_results_table
            # Use responsive width if default value is used
            table_width = None if args.width == get_ui_setting("bar_width", 40) else args.width
            render_results_table(top_files, table_width, colors)

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
    # Configure logging system with human-readable format
    setup_development_logging(verbose=False)

    # Set Sentry context
    if sentry_enabled:
        sentry_sdk.set_context("system", {
            "platform": sys.platform,
            "python_version": sys.version,
            "version": __version__,
        })
        sentry_sdk.set_tag("platform", sys.platform)
        sentry_sdk.set_tag("version", __version__)
        logger.info("Sentry error tracking enabled", extra={"sentry_enabled": True})
    else:
        logger.info("Sentry error tracking disabled (no DSN configured)", extra={"sentry_enabled": False})

    logger.info("LazyScan starting", extra={"version": __version__})

    # Initialize security system
    security_enabled = initialize_security_system()

    try:
        # Run Typer app
        app()
    finally:
        # Properly shutdown security system
        try:
            if security_enabled:
                audit_logger.log_shutdown({"clean_exit": True})
                logger.info("Security system shutdown completed")
        except Exception as e:
            logger.warning("Security system shutdown failed", extra={"error": str(e)})
            pass  # Don't let shutdown errors affect the main program


def show_logo_and_disclaimer_if_needed(no_logo: bool = False, no_disclaimer: bool = False):
    """Show logo and disclaimer if needed."""
    if not no_logo:
        show_logo()
        # Check and display disclaimer only if not acknowledged and not skipped
        if not has_seen_disclaimer() and not no_disclaimer:
            show_disclaimer()
            input("Press Enter to acknowledge the disclaimer and continue...")
            mark_disclaimer_acknowledged()


@cli_error_handler
def cli_main():
    """Entry point for the CLI when installed as a package."""
    main()


if __name__ == "__main__":
    cli_main()
