#!/usr/bin/env python3
"""
Main CLI module for LazyScan.
Handles argument parsing, main execution flow, and coordination between modules.
"""

import argparse
import os
import sys
import time
import threading
import random

from ..core.logging_config import get_logger
from ..core.formatting import human_readable, get_terminal_colors
from ..core.ui import (
    show_logo, 
    show_disclaimer, 
    knight_rider_animation, 
    display_scan_results_header,
    display_scan_summary,
    display_cache_cleanup_summary,
    get_console
)
from ..core.config import get_config, has_seen_disclaimer, mark_disclaimer_acknowledged
from ..core.scanner import get_disk_usage, scan_directory_with_progress
from ..apps.unity import handle_unity_discovery
from ..apps.unreal import handle_unreal_discovery  
from ..apps.chrome import handle_chrome_discovery

# Import security framework
from helpers.audit import audit_logger, get_audit_summary
from helpers.secure_operations import configure_security, secure_delete
from helpers.recovery import get_recovery_stats


logger = get_logger(__name__)
console = get_console()
__version__ = "0.5.0"

# Application cache paths - these will be moved to a separate platforms module later
MACOS_CACHE_PATHS = [
    # System caches
    "~/Library/Caches/*",
    "~/Library/Application Support/CrashReporter/*",
    "~/Library/Logs/*",
    
    # Browser caches  
    "~/Library/Caches/Google/Chrome/*",
    "~/Library/Caches/com.apple.Safari/*",
    
    # Common application caches
    "~/Library/Caches/com.apple.dt.Xcode/*",
    "~/Library/Caches/com.microsoft.VSCode/*",
    "~/Library/Caches/Slack/*",
    "~/Library/Caches/Spotify/*"
]

# Other application paths (to be moved to platforms module)
PERPLEXITY_PATHS = [
    os.path.expanduser('~/Library/Caches/Perplexity*'),
    os.path.expanduser('~/Library/Application Support/Perplexity/Cache/*'),
    os.path.expanduser('~/Library/Application Support/Perplexity/Code Cache/*'),
]

DIA_PATHS = [
    os.path.expanduser('~/Library/Application Support/Dia/*'),
    os.path.expanduser('~/Library/Caches/Dia*'),
]

SLACK_PATHS = [
    os.path.expanduser('~/Library/Application Support/Slack/Cache/*'),
    os.path.expanduser('~/Library/Caches/com.tinyspeck.slackmacgap*'),
]

DISCORD_PATHS = [
    os.path.expanduser('~/Library/Application Support/discord/Cache/*'),
    os.path.expanduser('~/Library/Application Support/discord/Code Cache/*'),
]

SPOTIFY_PATHS = [
    os.path.expanduser('~/Library/Application Support/Spotify/PersistentCache/*'),
    os.path.expanduser('~/Library/Caches/com.spotify.client/*'),
]

VSCODE_PATHS = [
    os.path.expanduser('~/Library/Application Support/Code/Cache/*'),
    os.path.expanduser('~/Library/Application Support/Code/logs/*'),
]

ZOOM_PATHS = [
    os.path.expanduser('~/Library/Application Support/zoom.us/Cache/*'),
    os.path.expanduser('~/Documents/Zoom/*'),
]

TEAMS_PATHS = [
    os.path.expanduser('~/Library/Application Support/Microsoft/Teams/Cache/*'),
    os.path.expanduser('~/Library/Application Support/Microsoft/Teams/GPUCache/*'),
]

FIREFOX_PATHS = [
    os.path.expanduser('~/Library/Application Support/Firefox/Profiles/*/cache2/*'),
    os.path.expanduser('~/Library/Caches/Firefox/*'),
]

SAFARI_PATHS = [
    os.path.expanduser('~/Library/Caches/com.apple.Safari/*'),
    os.path.expanduser('~/Library/Safari/Databases/*'),
]


def initialize_security_system():
    """Initialize the comprehensive security framework for LazyScan."""
    try:
        logger.info("Initializing security system", extra={
            "version": __version__,
            "platform": sys.platform
        })
        
        # Log application startup
        audit_logger.log_startup({
            "version": __version__,
            "security_enabled": True,
            "backup_enabled": True,
            "platform": sys.platform
        })

        # Configure security settings
        configure_security(enable_backups=True, enable_confirmations=True)

        # Show recovery statistics if available
        stats = get_recovery_stats()
        if stats['recoverable_operations'] > 0:
            console.print(f"\n🔄 Recovery System: {stats['recoverable_operations']} operations can be recovered")
            console.print(f"   Total recoverable: {stats['total_files_recoverable']:,} files ({stats['total_size_recoverable'] / (1024**3):.1f} GB)")

        return True
    except Exception as e:
        logger.error("Security system initialization failed", extra={
            "error": str(e)
        }, exc_info=True)
        console.print(f"⚠️  Warning: Security system initialization failed: {e}")
        console.print("   Continuing with basic safety measures...")
        return False


def select_directory():
    """Let the user choose a directory from stdin."""
    cwd = os.getcwd()
    dirs = ['.'] + sorted([d for d in os.listdir(cwd) if os.path.isdir(os.path.join(cwd, d))])
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
            return dirs[n-1]
        console.print(f"Invalid choice: {choice}")


def clean_macos_cache(paths, colors):
    """Clean macOS cache directories."""
    import glob
    import shutil
    
    CYAN, MAGENTA, YELLOW, RESET, BOLD = colors[:5]
    
    console.print(f"\n{BOLD}{CYAN}[{MAGENTA}►{CYAN}]{RESET} {YELLOW}Scanning cache directories...{RESET}")
    
    cache_items = []
    for path_pattern in paths:
        expanded_pattern = os.path.expanduser(path_pattern)
        for item in glob.glob(expanded_pattern):
            if os.path.exists(item):
                try:
                    if os.path.isfile(item):
                        size = os.path.getsize(item)
                    elif os.path.isdir(item):
                        size = sum(os.path.getsize(os.path.join(root, f)) 
                                 for root, dirs, files in os.walk(item) 
                                 for f in files)
                    else:
                        continue
                    cache_items.append((item, size))
                except (OSError, PermissionError):
                    continue
    
    if not cache_items:
        console.print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}No cache items found to clean.{RESET}")
        return 0
    
    # Sort by size
    cache_items.sort(key=lambda x: x[1], reverse=True)
    total_size = sum(size for _, size in cache_items)
    
    console.print(f"\n{BOLD}{CYAN}[{MAGENTA}📊{CYAN}]{RESET} {YELLOW}Found {len(cache_items)} cache items ({human_readable(total_size)}){RESET}")
    
    # Show top 5 items
    console.print(f"\n{CYAN}Top cache items:{RESET}")
    for path, size in cache_items[:5]:
        display_path = path.replace(os.path.expanduser('~'), '~')
        console.print(f"  {human_readable(size):>10} {display_path}")
    
    if len(cache_items) > 5:
        console.print(f"  ...and {len(cache_items) - 5} more items")
    
    # Confirm deletion
    if not input(f"\n{YELLOW}Clean {len(cache_items)} cache items? [y/N]: {RESET}").strip().lower().startswith('y'):
        console.print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}Cache cleaning cancelled.{RESET}")
        return 0
    
    # Animate deletion
    knight_rider_animation('Cleaning cache directories...', colors=colors)
    
    freed_bytes = 0
    errors = 0
    
    for path, size in cache_items:
        try:
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            freed_bytes += size
        except (OSError, PermissionError):
            errors += 1
    
    # Clear animation
    sys.stdout.write("\r" + " " * 100 + "\r")
    sys.stdout.flush()
    
    return freed_bytes


def scan_application_cache(app_name, paths, colors, check_path=None):
    """Scan application-specific cache directories."""
    CYAN, MAGENTA, YELLOW, RESET, BOLD, BRIGHT_CYAN, BRIGHT_MAGENTA, GREEN, RED = get_terminal_colors()[:9]
    
    # Check if application exists
    if check_path and not os.path.exists(os.path.expanduser(check_path)):
        console.print(f"\n{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}{app_name} not found or not installed.{RESET}")
        return 0
    
    console.print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}{app_name.upper()}{CYAN}]{RESET} {YELLOW}Scanning {app_name} cache...{RESET}")
    
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
                                    dir_size += os.path.getsize(os.path.join(root, file))
                                except (OSError, PermissionError):
                                    continue
                        cache_items.append((item, dir_size))
                except (OSError, PermissionError):
                    continue
    
    if not cache_items:
        console.print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}No {app_name} cache found.{RESET}")
        return 0
    
    # Calculate total
    total_size = sum(size for _, size in cache_items)
    console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}✓{CYAN}]{RESET} {GREEN}Found {len(cache_items)} {app_name} cache items ({BRIGHT_MAGENTA}{human_readable(total_size)}{RESET})")
    
    # Show details
    cache_items.sort(key=lambda x: x[1], reverse=True)
    for path, size in cache_items[:3]:
        display_path = path.replace(os.path.expanduser('~'), '~')
        if len(display_path) > 60:
            display_path = "..." + display_path[-57:]
        console.print(f"  {human_readable(size):>10} {YELLOW}{display_path}{RESET}")
    
    if len(cache_items) > 3:
        console.print(f"  {CYAN}...and {len(cache_items) - 3} more items{RESET}")
    
    # Ask for confirmation
    response = input(f"\n{YELLOW}Clean {app_name} cache? [y/N]: {RESET}").strip().lower()
    if not response.startswith('y'):
        console.print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}{app_name} cleanup cancelled.{RESET}")
        return 0
    
    # Clean with animation
    knight_rider_animation(f'Cleaning {app_name} cache...', colors=colors[:5])
    
    freed_bytes = 0
    errors = 0
    
    for path, size in cache_items:
        try:
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                import shutil
                shutil.rmtree(path, ignore_errors=True)
            freed_bytes += size
        except (OSError, PermissionError):
            errors += 1
    
    # Clear animation
    sys.stdout.write("\r" + " " * 100 + "\r")  
    sys.stdout.flush()
    
    # Results
    console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}✓{CYAN}]{RESET} {BRIGHT_CYAN}{app_name.upper()} CACHE CLEANED{RESET}")
    console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Space reclaimed:{RESET} {BRIGHT_MAGENTA}{human_readable(freed_bytes)}{RESET}")
    console.print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Items cleaned:{RESET} {BRIGHT_CYAN}{len(cache_items) - errors}{RESET}")

    if errors > 0:
        console.print(f"{BOLD}{CYAN}[{RED}!{CYAN}]{RESET} {RED}Failed to clean {errors} items (permission denied){RESET}")

    console.print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}■{CYAN}]{RESET} {GREEN}{app_name} cleanup completed successfully.{RESET}")

    return freed_bytes


def create_argument_parser():
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description='A lazy way to find what\'s eating your disk space with added support for macOS cache cleaning',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Scan your home directory and show top 10 biggest files:
    lazyscan ~ -n 10

  Scan current directory with interactive selection:
    lazyscan -i

  Clean macOS cache directories (macOS only):
    lazyscan --macos

  Clean cache and then scan Downloads folder:
    lazyscan --macos ~/Downloads

  Scan Chrome browser cache (macOS only):
    lazyscan --chrome

  Scan Unreal Engine projects:
    lazyscan --unreal

  Scan without the fancy logo:
    lazyscan --no-logo /path/to/scan
""")
    
    # Basic scan options
    parser.add_argument('-n', '--top', type=int, default=20,
                        help='number of top files to display (default: 20)')
    parser.add_argument('-w', '--width', type=int, default=40,
                        help='bar width in characters (default: 40)')
    parser.add_argument('-i', '--interactive', action='store_true',
                        help='prompt to choose directory (for the truly lazy)')
    parser.add_argument('--no-logo', action='store_true',
                        help='hide the lazyscan logo')
    
    # macOS system cache cleaning
    parser.add_argument('--macos', action='store_true',
                        help='clean macOS cache directories (can be used with or without scanning)')
    
    # Application-specific scanning
    parser.add_argument('--chrome', action='store_true',
                        help='scan Chrome Application Support for cleanable files')
    parser.add_argument('--perplexity', action='store_true',
                        help='scan Perplexity AI cache for cleanable files')
    parser.add_argument('--dia', action='store_true',
                        help='scan Dia diagram editor cache for cleanable files')
    parser.add_argument('--slack', action='store_true',
                        help='scan Slack cache for cleanable files')
    parser.add_argument('--discord', action='store_true',
                        help='scan Discord cache for cleanable files')
    parser.add_argument('--spotify', action='store_true',
                        help='scan Spotify cache for cleanable files')
    parser.add_argument('--vscode', action='store_true',
                        help='scan VS Code cache for cleanable files')
    parser.add_argument('--zoom', action='store_true',
                        help='scan Zoom cache and recorded meetings for cleanable files')
    parser.add_argument('--teams', action='store_true',
                        help='scan Microsoft Teams cache for cleanable files')
    parser.add_argument('--firefox', action='store_true',
                        help='scan Firefox cache for cleanable files')
    parser.add_argument('--safari', action='store_true',
                        help='scan Safari cache for cleanable files')
    
    # Path argument
    parser.add_argument('path', nargs='?', default=None,
                        help='directory path to scan (default: current directory)')
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}',
                        help='show version number and exit')
    
    # Unity-specific options
    unity_group = parser.add_argument_group('Unity Flags', 'Unity-specific discovery options')
    unity_group.add_argument('--unity', action='store_true',
                             help='enter Unity-specific discovery logic')
    unity_group.add_argument('--pick', action='store_true',
                             help='force GUI picker (used with --unity)')
    unity_group.add_argument('--clean', action='store_true',
                             help='delete caches immediately after listing (used with --unity)')
    unity_group.add_argument('--build-dir', action='store_true',
                             help='include Build directory in size calculation (used with --unity)')
    unity_group.add_argument('--no-unityhub', action='store_true',
                             help='suppress Unity Hub project discovery (used with --unity)')
    unity_group.add_argument('--unityhub-json', metavar='path', type=str,
                             help='override default Unity Hub JSON path')
    
    # Unreal Engine options
    unreal_group = parser.add_argument_group('Unreal Engine Flags', 'Unreal-specific discovery options')
    unreal_group.add_argument('--unreal', action='store_true',
                             help='enter Unreal-specific discovery logic')
    unreal_group.add_argument('--unreal-pick', action='store_true',
                             help='force GUI picker (used with --unreal)')

    # Security and Recovery options
    security_group = parser.add_argument_group('Security & Recovery', 'Security and recovery options')
    security_group.add_argument('--recovery', action='store_true',
                               help='show recovery menu for restoring deleted files')
    security_group.add_argument('--audit-logs', action='store_true',
                               help='display recent audit logs')
    security_group.add_argument('--recovery-stats', action='store_true',
                               help='show recovery system statistics')

    return parser


def handle_security_and_recovery_commands(args):
    """Handle security and recovery related commands."""
    if args.recovery:
        console.print("\n=== Recovery System ===")
        stats = get_recovery_stats()
        console.print(f"Total recoverable operations: {stats.get('total_operations', 0)}")
        console.print(f"Successful recoveries: {stats.get('successful_recoveries', 0)}")
        console.print(f"Failed recoveries: {stats.get('failed_recoveries', 0)}")
        console.print(f"Total files backed up: {stats.get('total_files_backed_up', 0)}")
        console.print(f"Total backup size: {stats.get('total_backup_size_mb', 0):.2f} MB")

        from helpers.recovery import list_recent_operations
        recent_ops = list_recent_operations(7)
        if recent_ops:
            console.print("\nRecent operations (last 7 days):")
            for op in recent_ops[:10]:  # Show last 10
                console.print(f"  {op['timestamp']}: {op['operation_type']} - {op['files_affected']} files")
        else:
            console.print("\nNo recent operations found.")
        return True

    if args.audit_logs:
        summary = get_audit_summary(24)  # Last 24 hours
        console.print(f"\n📋 Audit Log Summary (Last 24 Hours):")
        console.print(f"   Total Events: {summary.get('total_events', 0)}")
        console.print(f"   Scan Operations: {summary.get('scan_operations', 0)}")
        console.print(f"   Delete Operations: {summary.get('delete_operations', 0)}")
        console.print(f"   Security Events: {summary.get('security_events', 0)}")
        console.print(f"   Errors: {summary.get('errors', 0)}")
        if summary.get('session_id'):
            console.print(f"   Session ID: {summary['session_id']}")
        if summary.get('total_events', 0) == 0:
            console.print("   No audit events found in the last 24 hours.")
        return True

    if args.recovery_stats:
        stats = get_recovery_stats()
        console.print(f"\n📊 Recovery System Statistics:")
        console.print(f"   Recoverable Operations: {stats.get('recoverable_operations', 0)}")
        console.print(f"   Total Files: {stats.get('total_files_recoverable', 0):,}")
        console.print(f"   Total Size: {stats.get('total_size_recoverable', 0) / (1024**3):.2f} GB")
        if stats.get('oldest_operation'):
            console.print(f"   Oldest Operation: {stats['oldest_operation']}")
        if stats.get('newest_operation'):
            console.print(f"   Newest Operation: {stats['newest_operation']}")
        if not stats.get('recoverable_operations', 0):
            console.print("   No recovery operations available.")
        return True
    
    return False


def handle_application_specific_scans(args, colors):
    """Handle application-specific cache scans."""
    app_scan_requested = any([
        args.perplexity, args.dia, args.slack, args.discord, args.spotify,
        args.vscode, args.zoom, args.teams, args.firefox, args.safari
    ])
    
    if not app_scan_requested:
        return False
    
    logger.info("Starting application-specific cache scans", extra={
        "requested_apps": [app for app in ['perplexity', 'dia', 'slack', 'discord', 'spotify', 'vscode', 'zoom', 'teams', 'firefox', 'safari'] 
                          if getattr(args, app, False)]
    })
    
    # Handle each application
    if args.perplexity:
        scan_application_cache('Perplexity', PERPLEXITY_PATHS, colors, check_path='~/Library/Application Support/Perplexity')

    if args.dia:
        scan_application_cache('Dia', DIA_PATHS, colors, check_path='~/Library/Application Support/Dia')

    if args.slack:
        scan_application_cache('Slack', SLACK_PATHS, colors, check_path='~/Library/Application Support/Slack')

    if args.discord:
        scan_application_cache('Discord', DISCORD_PATHS, colors, check_path='~/Library/Application Support/discord')

    if args.spotify:
        scan_application_cache('Spotify', SPOTIFY_PATHS, colors, check_path='~/Library/Application Support/Spotify')

    if args.vscode:
        scan_application_cache('VS Code', VSCODE_PATHS, colors, check_path='~/Library/Application Support/Code')

    if args.zoom:
        scan_application_cache('Zoom', ZOOM_PATHS, colors, check_path='~/Library/Application Support/zoom.us')

    if args.teams:
        scan_application_cache('Teams', TEAMS_PATHS, colors, check_path='~/Library/Application Support/Microsoft/Teams')

    if args.firefox:
        scan_application_cache('Firefox', FIREFOX_PATHS, colors, check_path='~/Library/Application Support/Firefox')

    if args.safari:
        scan_application_cache('Safari', SAFARI_PATHS, colors, check_path='~/Library/Caches/com.apple.Safari')

    return True


def handle_macos_cache_cleaning(args):
    """Handle macOS system cache cleaning."""
    if not args.macos:
        return False
    
    # Platform guard - macOS only feature
    if sys.platform != 'darwin':
        logger.error("macOS cache cleaning attempted on non-macOS platform", extra={
            "platform": sys.platform
        })
        console.print("\nError: --macos option is only available on macOS.")
        sys.exit(1)

    logger.info("Starting macOS cache cleaning", extra={
        "operation": "macos_cache_clean"
    })

    # Get disk usage before cleaning
    total_before, used_before, free_before, _ = get_disk_usage()

    # Setup colors for cache cleaning
    colors = get_terminal_colors()
    
    # Display initial disk usage
    console.print(f"\n{colors[4]}{colors[0]}[{colors[5]}SYSTEM STATUS{colors[0]}]{colors[3]} {colors[2]}Current disk usage:{colors[3]}")
    _, _, _, usage_before_str = get_disk_usage()
    console.print(usage_before_str)

    # Clean macOS cache directories
    freed_bytes = clean_macos_cache(MACOS_CACHE_PATHS, colors)

    # Get disk usage after cleaning
    total_after, used_after, free_after, _ = get_disk_usage()

    # Display summary banner if space was actually freed
    if freed_bytes > 0:
        display_cache_cleanup_summary(
            freed_bytes, used_before, used_after, total_before, total_after,
            free_before, free_after, colors
        )

        # Display updated disk usage
        console.print(f"\n{colors[4]}{colors[0]}[{colors[5]}SYSTEM STATUS{colors[0]}]{colors[3]} {colors[2]}Updated disk usage:{colors[3]}")
        _, _, _, usage_after_str = get_disk_usage()
        console.print(usage_after_str)

    logger.info("macOS cache cleaning completed", extra={
        "freed_bytes": freed_bytes,
        "used_before": used_before,
        "used_after": used_after
    })

    return True


def main():
    """Main entry point for LazyScan."""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    logger.info("LazyScan starting", extra={
        "version": __version__,
        "args": vars(args)
    })

    # Show logo and disclaimer
    if not args.no_logo:
        show_logo()
        # Check and display disclaimer only if not acknowledged
        if not has_seen_disclaimer():
            show_disclaimer()
            input('Press Enter to acknowledge the disclaimer and continue...')
            mark_disclaimer_acknowledged()

    # Initialize security system
    security_enabled = initialize_security_system()

    # Handle security and recovery options first
    if handle_security_and_recovery_commands(args):
        return

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
        if not args.path and not args.interactive and not args.macos:
            return

    # Setup colors for application scanning
    colors = get_terminal_colors()

    # Handle macOS cache cleaning
    cleaned_cache = handle_macos_cache_cleaning(args)
    if cleaned_cache and not args.path and not args.interactive:
        console.print(f"\n{colors[4]}{colors[0]}[{colors[5]}✓{colors[0]}]{colors[3]} {colors[7]}Operation completed successfully.{colors[3]}")
        return

    # Handle application-specific cache scans
    app_scans_done = handle_application_specific_scans(args, colors)
    if app_scans_done and not args.path and not args.interactive:
        return

    # Determine scan path for directory scanning
    if args.interactive:
        scan_path = select_directory()
    else:
        scan_path = args.path or '.'

    logger.info("Starting directory scan", extra={
        "scan_path": scan_path,
        "top_files": args.top,
        "interactive": args.interactive
    })

    # Perform directory scan with structured logging and UI
    try:
        file_sizes = scan_directory_with_progress(scan_path, colors)
        
        if not file_sizes:
            console.print(f"No files found under '{scan_path}'.")
            logger.warning("No files found in scan path", extra={"scan_path": scan_path})
            return

        # Sort and select top N files
        file_sizes.sort(key=lambda x: x[1], reverse=True)
        top_files = file_sizes[:args.top]
        total_size = sum(size for _, size in top_files)
        
        # Display results
        display_scan_results_header(len(top_files), colors)
        
        # Render results table
        from ..core.formatting import render_results_table
        render_results_table(top_files, args.width, colors)
        
        # Display summary
        display_scan_summary(total_size, scan_path, colors)
        
        logger.info("Directory scan completed", extra={
            "scan_path": scan_path,
            "files_found": len(file_sizes),
            "top_files_shown": len(top_files),
            "total_size": total_size
        })

    except Exception as e:
        logger.error("Directory scan failed", extra={
            "scan_path": scan_path,
            "error": str(e)
        }, exc_info=True)
        console.print(f"Error scanning directory: {e}")
        return

    # Properly shutdown security system
    try:
        if security_enabled:
            audit_logger.log_shutdown({"clean_exit": True})
            logger.info("Security system shutdown completed")
    except Exception as e:
        logger.warning("Security system shutdown failed", extra={
            "error": str(e)
        })
        pass  # Don't let shutdown errors affect the main program


def cli_main():
    """Entry point for the CLI when installed as a package."""
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        console.print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error in main", extra={
            "error": str(e)
        }, exc_info=True)
        console.print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    cli_main()
