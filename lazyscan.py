#!/usr/bin/env python3
"""
lazyscan: A lazy way to find what's eating your disk space.

Includes a new feature to clean macOS cache directories seamlessly.
Created by TheLazyIndianTechie - for the lazy developer in all of us.
v0.3.0
"""
__version__ = "0.5.0"

import os
import sys
import argparse
import time
import random
import threading
import shutil
import glob
import configparser
from datetime import datetime

# Import Unity helpers
from helpers.unity_cache_helpers import generate_unity_project_report
from helpers.unity_hub import read_unity_hub_projects

# Import Unreal Engine helpers
from helpers.unreal_cache_helpers import generate_unreal_project_report

# Import Chrome helpers
from helpers.chrome_cache_helpers import scan_chrome_cache as scan_chrome_cache_helper

# Import Security Framework
from helpers.audit import audit_logger
from helpers.secure_operations import configure_security, secure_delete
from helpers.recovery import get_recovery_stats


def prompt_unity_project_selection(projects):
    """Prompt user to select Unity projects."""
    # Check if the terminal is interactive
    if not sys.stdin.isatty():
        print("Non-interactive terminal. Skipping project selection.")
        return []

    print("\nAvailable Unity Projects:")
    for index, project in enumerate(projects, 1):
        print(f"{index}) {project['name']} ({project['path']})")

    print("0) All projects")
    print("Q) Quit")

    selected_projects = []
    while not selected_projects:
        selection = input("Select projects by number (comma or space-separated): ").strip()
        if selection.strip().lower() == 'q':
            return []

        try:
            indexes = set(
                int(x) for x in selection.replace(',', ' ').split() if x.isdigit()
            )

            if 0 in indexes:
                return projects

            selected_projects = [projects[i - 1] for i in indexes if 0 < i <= len(projects)]

            if not selected_projects:
                print("No valid selections made. Please try again.")
        except ValueError:
            print("Invalid input. Please enter numbers separated by commas or spaces.")

    return selected_projects


# Configuration paths
CONFIG_DIR = os.path.expanduser('~/.config/lazyscan')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'preferences.ini')


def get_config():
    """Load lazyscan configuration."""
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
    return config


def save_config(config):
    """Save lazyscan configuration."""
    # Create config directory if it doesn't exist
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        config.write(f)


def has_seen_disclaimer():
    """Check if user has seen and acknowledged the disclaimer."""
    config = get_config()
    return config.getboolean('disclaimer', 'acknowledged', fallback=False)


def mark_disclaimer_acknowledged():
    """Mark the disclaimer as acknowledged with timestamp."""
    config = get_config()
    if not config.has_section('disclaimer'):
        config.add_section('disclaimer')
    config.set('disclaimer', 'acknowledged', 'true')
    config.set('disclaimer', 'acknowledged_date', datetime.now().isoformat())
    config.set('disclaimer', 'version', __version__)
    save_config(config)


def initialize_security_system():
    """Initialize the comprehensive security framework for LazyScan."""
    try:
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
            print(f"\n🔄 Recovery System: {stats['recoverable_operations']} operations can be recovered")
            print(f"   Total recoverable: {stats['total_files_recoverable']:,} files ({stats['total_size_recoverable'] / (1024**3):.1f} GB)")

        return True
    except Exception as e:
        print(f"⚠️  Warning: Security system initialization failed: {e}")
        print("   Continuing with basic safety measures...")
        return False


# Chrome-specific paths for targeted cleaning
CHROME_PATHS = [
    # Chrome Cache
    os.path.expanduser('~/Library/Caches/Google/Chrome/*'),
    os.path.expanduser('~/Library/Application Support/Google/Chrome/Default/Cache/*'),
    os.path.expanduser('~/Library/Application Support/Google/Chrome/Default/Code Cache/*'),
    os.path.expanduser('~/Library/Application Support/Google/Chrome/Default/GPUCache/*'),
    os.path.expanduser('~/Library/Application Support/Google/Chrome/Default/Service Worker/CacheStorage/*'),
    os.path.expanduser('~/Library/Application Support/Google/Chrome/Default/Service Worker/ScriptCache/*'),

    # Chrome Profile Data (be careful with these)
    os.path.expanduser('~/Library/Application Support/Google/Chrome/*/Cache/*'),
    os.path.expanduser('~/Library/Application Support/Google/Chrome/*/Code Cache/*'),
    os.path.expanduser('~/Library/Application Support/Google/Chrome/*/GPUCache/*'),

    # Chrome Media Cache
    os.path.expanduser('~/Library/Application Support/Google/Chrome/Default/Media Cache/*'),
    os.path.expanduser('~/Library/Application Support/Google/Chrome/*/Media Cache/*'),

    # Chrome Temporary Downloads
    os.path.expanduser('~/Library/Application Support/Google/Chrome/Default/.com.google.Chrome.*'),

    # Old Chrome Versions and Updates
    os.path.expanduser('~/Library/Application Support/Google/Chrome/CrashReports/*'),
    os.path.expanduser('~/Library/Application Support/Google/Chrome/Crashpad/completed/*'),
]

# Perplexity-specific paths
PERPLEXITY_PATHS = [
    # Perplexity Cache and Data
    os.path.expanduser('~/Library/Caches/Perplexity*'),
    os.path.expanduser('~/Library/Application Support/Perplexity/Cache/*'),
    os.path.expanduser('~/Library/Application Support/Perplexity/Code Cache/*'),
    os.path.expanduser('~/Library/Application Support/Perplexity/GPUCache/*'),
    os.path.expanduser('~/Library/Application Support/Perplexity/Service Worker/CacheStorage/*'),
    os.path.expanduser('~/Library/Application Support/Perplexity/Service Worker/ScriptCache/*'),
    os.path.expanduser('~/Library/Application Support/Perplexity/Crashpad/completed/*'),
    os.path.expanduser('~/Library/WebKit/Perplexity*'),
]

# Dia diagram editor paths
DIA_PATHS = [
    os.path.expanduser('~/Library/Application Support/Dia/*'),
    os.path.expanduser('~/Library/Caches/Dia*'),
    os.path.expanduser('~/.dia/autosave/*'),
    os.path.expanduser('~/.dia/tmp/*'),
]

# Slack-specific paths
SLACK_PATHS = [
    os.path.expanduser('~/Library/Application Support/Slack/Cache/*'),
    os.path.expanduser('~/Library/Application Support/Slack/Code Cache/*'),
    os.path.expanduser('~/Library/Application Support/Slack/GPUCache/*'),
    os.path.expanduser('~/Library/Application Support/Slack/Service Worker/CacheStorage/*'),
    os.path.expanduser('~/Library/Caches/com.tinyspeck.slackmacgap*'),
    os.path.expanduser('~/Library/Containers/com.tinyspeck.slackmacgap/Data/Library/Caches/*'),
]

# Discord-specific paths
DISCORD_PATHS = [
    os.path.expanduser('~/Library/Application Support/discord/Cache/*'),
    os.path.expanduser('~/Library/Application Support/discord/Code Cache/*'),
    os.path.expanduser('~/Library/Application Support/discord/GPUCache/*'),
    os.path.expanduser('~/Library/Application Support/discord/VideoDecodeStats/*'),
    os.path.expanduser('~/Library/Caches/com.hnc.Discord*'),
]

# Spotify-specific paths
SPOTIFY_PATHS = [
    os.path.expanduser('~/Library/Caches/com.spotify.client*'),
    os.path.expanduser('~/Library/Application Support/Spotify/PersistentCache/*'),
    os.path.expanduser('~/Library/Application Support/Spotify/Browser/*'),
    os.path.expanduser('~/Library/Application Support/Spotify/Data/*'),
]

# VS Code-specific paths
VSCODE_PATHS = [
    os.path.expanduser('~/Library/Application Support/Code/Cache/*'),
    os.path.expanduser('~/Library/Application Support/Code/CachedData/*'),
    os.path.expanduser('~/Library/Application Support/Code/Code Cache/*'),
    os.path.expanduser('~/Library/Application Support/Code/GPUCache/*'),
    os.path.expanduser('~/Library/Application Support/Code/logs/*'),
    os.path.expanduser('~/Library/Application Support/Code/Service Worker/CacheStorage/*'),
    os.path.expanduser('~/Library/Application Support/Code/Service Worker/ScriptCache/*'),
    os.path.expanduser('~/Library/Application Support/Code/User/workspaceStorage/*'),
]

# Zoom-specific paths
ZOOM_PATHS = [
    os.path.expanduser('~/Library/Application Support/zoom.us/AutoDownload/*'),
    os.path.expanduser('~/Library/Caches/us.zoom.xos*'),
    os.path.expanduser('~/Library/Logs/zoom*'),
    os.path.expanduser('~/Documents/Zoom/*'),  # Recorded meetings
]

# Microsoft Teams paths
TEAMS_PATHS = [
    os.path.expanduser('~/Library/Application Support/Microsoft/Teams/Cache/*'),
    os.path.expanduser('~/Library/Application Support/Microsoft/Teams/Code Cache/*'),
    os.path.expanduser('~/Library/Application Support/Microsoft/Teams/GPUCache/*'),
    os.path.expanduser('~/Library/Application Support/Microsoft/Teams/Service Worker/CacheStorage/*'),
    os.path.expanduser('~/Library/Application Support/Microsoft/Teams/tmp/*'),
    os.path.expanduser('~/Library/Application Support/Microsoft/Teams/media-stack/*'),
]

# Firefox-specific paths
FIREFOX_PATHS = [
    os.path.expanduser('~/Library/Caches/Firefox/*'),
    os.path.expanduser('~/Library/Application Support/Firefox/Profiles/*/cache2/*'),
    os.path.expanduser('~/Library/Application Support/Firefox/Profiles/*/startupCache/*'),
    os.path.expanduser('~/Library/Application Support/Firefox/Profiles/*/shader-cache/*'),
    os.path.expanduser('~/Library/Application Support/Firefox/Profiles/*/thumbnails/*'),
    os.path.expanduser('~/Library/Application Support/Firefox/Crash Reports/*'),
]

# Safari-specific paths
SAFARI_PATHS = [
    os.path.expanduser('~/Library/Caches/com.apple.Safari/*'),
    os.path.expanduser('~/Library/Caches/com.apple.Safari.SafeBrowsing/*'),
    os.path.expanduser('~/Library/Safari/CloudTabs.db-wal'),
    os.path.expanduser('~/Library/Safari/CloudTabs.db-shm'),
    os.path.expanduser('~/Library/Caches/com.apple.WebKit.WebContent/*'),
    os.path.expanduser('~/Library/Caches/com.apple.WebKit.Networking/*'),
]

# macOS cache directories based on user-provided list
# Reference: User-provided list of 34 macOS cache paths
MACOS_CACHE_PATHS = [
    # System & User Caches
    os.path.expanduser('~/Library/Caches/*'),
    '/Library/Caches/*',
    '/System/Library/Caches/*',
    '/private/var/folders/*/*/*/*',

    # Xcode & Development
    os.path.expanduser('~/Library/Developer/Xcode/DerivedData/*'),
    os.path.expanduser('~/Library/Developer/Xcode/Archives/*'),
    os.path.expanduser('~/Library/Developer/CoreSimulator/Devices/*'),
    os.path.expanduser('~/Library/Developer/CoreSimulator/Caches/*'),

    # Application Caches
    os.path.expanduser('~/Library/Application Support/*/Cache*'),
    os.path.expanduser('~/Library/Application Support/*/Caches*'),
    os.path.expanduser('~/Library/Containers/*/Data/Library/Caches/*'),

    # Browser Caches
    os.path.expanduser('~/Library/Caches/com.apple.Safari/*'),
    os.path.expanduser('~/Library/Caches/Google/Chrome/*'),
    os.path.expanduser('~/Library/Caches/Firefox/*'),
    os.path.expanduser('~/Library/Application Support/Google/Chrome/*/Cache*'),
    os.path.expanduser('~/Library/Application Support/Firefox/Profiles/*/cache*'),

    # Media & Downloads
    os.path.expanduser('~/Downloads/*.dmg'),
    os.path.expanduser('~/Downloads/*.pkg'),
    os.path.expanduser('~/Library/Caches/com.apple.bird/*'),
    os.path.expanduser('~/Library/Caches/CloudKit/*'),

    # iOS & Device Support
    os.path.expanduser('~/Library/Application Support/MobileSync/Backup/*'),
    os.path.expanduser('~/Library/iTunes/iPhone Software Updates/*'),

    # Logs & Diagnostics
    os.path.expanduser('~/Library/Logs/*'),
    '/private/var/log/*',
    '/Library/Logs/*',
    os.path.expanduser('~/Library/Application Support/CrashReporter/*'),

    # Mail & Messages
    os.path.expanduser('~/Library/Mail/V*/MailData/Envelope Index*'),
    os.path.expanduser('~/Library/Messages/Attachments/*'),

    # Spotlight & Search
    '/.Spotlight-V100/*',
    os.path.expanduser('~/Library/Metadata/CoreSpotlight/*'),

    # Package Management
    os.path.expanduser('~/Library/Caches/Homebrew/*'),
    os.path.expanduser('~/.npm/_cacache/*'),
    os.path.expanduser('~/.cache/*'),

    # Temporary Files
    '/private/tmp/*',
]


def human_readable(size):
    """Convert a size in bytes to a human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} YB"


def clean_macos_cache(paths, colors):
    """Clean macOS cache directories with cyberpunk-styled output.

    Args:
        paths: List of glob patterns for cache directories
        colors: Tuple of color codes (CYAN, MAGENTA, YELLOW, RESET, BOLD)

    Returns:
        Total bytes freed
    """
    CYAN, MAGENTA, YELLOW, RESET, BOLD = colors
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_MAGENTA = '\033[95m'
    GREEN = '\033[92m'
    RED = '\033[91m'

    print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}CACHE SCANNER{CYAN}]{RESET} {YELLOW}Analyzing macOS cache directories...{RESET}")
    print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}▓▒░{CYAN}]{RESET} {BRIGHT_CYAN}Initiating deep scan of system caches...{RESET}\n")

    # Collect all cache directories and their sizes
    cache_items = []
    total_size = 0

    def is_safe_cache_path(path):
        """Ensure path is a known cache path, preventing accidental deletions."""
        # List of keywords or patterns typical for cache paths
        cache_keywords = [
            'cache', 'caches', 'tmp', 'temp', 'temporary',
            'deriveddata', 'backup', 'log', 'logs',
            'simulator', 'archives', 'crashreporter',
            '_cacache', 'homebrew', 'npm', '.Spotlight'
        ]
        # Also check for specific file extensions that are safe to delete
        safe_extensions = ['.dmg', '.pkg', '.log', '.crash']

        path_lower = path.lower()

        # Check if path contains cache keywords
        has_cache_keyword = any(keyword in path_lower for keyword in cache_keywords)

        # Check if it's a safe file extension
        has_safe_extension = any(path.endswith(ext) for ext in safe_extensions)

        # Additional safety checks - avoid critical system paths
        dangerous_paths = [
            '/Applications',
            '/System/Library/CoreServices',
            '/Users/' + os.path.expanduser('~').split('/')[-1] + '/Documents',
            '/Users/' + os.path.expanduser('~').split('/')[-1] + '/Desktop',
            '/Users/' + os.path.expanduser('~').split('/')[-1] + '/Pictures',
            '/Users/' + os.path.expanduser('~').split('/')[-1] + '/Music',
            '/Users/' + os.path.expanduser('~').split('/')[-1] + '/Movies'
        ]

        is_dangerous = any(path.startswith(danger) for danger in dangerous_paths)

        return (has_cache_keyword or has_safe_extension) and not is_dangerous

    skipped_count = 0

    for pattern in paths:
        try:
            for path in glob.glob(pattern):
                if os.path.exists(path):
                    if is_safe_cache_path(path):
                        try:
                            # Calculate directory size using os.scandir
                            dir_size = 0
                            for entry in os.scandir(path):
                                if entry.is_file(follow_symlinks=False):
                                    try:
                                        dir_size += entry.stat(follow_symlinks=False).st_size
                                    except (OSError, PermissionError):
                                        pass
                                elif entry.is_dir(follow_symlinks=False):
                                    # Recursively calculate subdirectory size
                                    for root, dirs, files in os.walk(entry.path):
                                        for f in files:
                                            try:
                                                dir_size += os.path.getsize(os.path.join(root, f))
                                            except (OSError, PermissionError):
                                                pass

                            if dir_size > 0:  # Only add if directory has content
                                cache_items.append((path, dir_size))
                                total_size += dir_size
                        except (OSError, PermissionError):
                            # Skip directories we can't access
                            continue
                    else:
                        skipped_count += 1
        except Exception:
            # Skip invalid patterns
            continue

    if skipped_count > 0:
        print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}Skipped {skipped_count} non-cache paths for safety{RESET}")

    if not cache_items:
        print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}No cache directories found or accessible.{RESET}")
        return 0

    # Sort by size (largest first)
    cache_items.sort(key=lambda x: x[1], reverse=True)

    # Display cache directories in cyberpunk style
    print(f"{BOLD}{MAGENTA}┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓{RESET}")
    print(f"{BOLD}{MAGENTA}┃ {YELLOW}CACHE TARGETS IDENTIFIED {CYAN}:: {BRIGHT_MAGENTA}TOTAL SIZE: {BRIGHT_CYAN}{human_readable(total_size):<10}{MAGENTA} ┃{RESET}")
    print(f"{BOLD}{MAGENTA}┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛{RESET}")

    print(f"\n{BOLD}{CYAN}[{YELLOW}TIP{CYAN}]{RESET} {YELLOW}Review cache contents before deleting:{RESET}")
    print(f"  {CYAN}• {RESET}Command+Click on the path to open in Finder")
    print(f"  {CYAN}• {RESET}Or copy and run the 'open' command shown below each path\n")

    # Display each cache directory
    for idx, (path, size) in enumerate(cache_items[:20], 1):  # Show top 20
        # Size indicator bar
        bar_width = 20
        bar_filled = int((size / cache_items[0][1]) * bar_width) if cache_items[0][1] > 0 else 0
        bar = f"{BRIGHT_CYAN}{'█' * bar_filled}{MAGENTA}{'░' * (bar_width - bar_filled)}{RESET}"

        # Display the entry
        print(f"{CYAN}[{BRIGHT_MAGENTA}{idx:02d}{CYAN}]{RESET} {bar} {BRIGHT_MAGENTA}{human_readable(size):>10}{RESET}")

        # Display full path on its own line for clarity
        print(f"     {GREEN}{path}{RESET}")

        # Show Finder command on a separate indented line
        finder_link = path.replace(" ", "\\ ").replace("(", "\\(").replace(")", "\\)")  # Escape special chars
        print(f"     {CYAN}→ {RESET}open {finder_link}")
        print()  # Empty line for readability

    if len(cache_items) > 20:
        print(f"\n{CYAN}[{YELLOW}...{CYAN}]{RESET} {YELLOW}And {len(cache_items) - 20} more directories{RESET}")
        print(f"\n{BOLD}{CYAN}[{YELLOW}OPTIONS{CYAN}]{RESET}")
        print(f"  {CYAN}a{RESET} - Show all {len(cache_items)} cache directories")
        print(f"  {CYAN}e{RESET} - Export full list to file")
        print(f"  {CYAN}s{RESET} - Show summary by cache type")
        print(f"  {CYAN}y{RESET} - Proceed with deletion")
        print(f"  {CYAN}n{RESET} - Cancel (default)")
        print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}?{CYAN}]{RESET} {YELLOW}Your choice {BRIGHT_CYAN}[a/e/s/y/N]{RESET}: ", end="", flush=True)
    else:
        print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}?{CYAN}]{RESET} {YELLOW}Delete these cache directories? {BRIGHT_CYAN}[y/N]{RESET}: ", end="", flush=True)

    while True:
        try:
            response = input().strip().lower()
        except KeyboardInterrupt:
            print(f"\n{BOLD}{CYAN}[{RED}X{CYAN}]{RESET} {RED}Operation cancelled.{RESET}")
            return 0

        if response == 'a':
            # Show all cache directories
            print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}ALL CACHE DIRECTORIES{CYAN}]{RESET}\n")
            for idx, (path, size) in enumerate(cache_items, 1):
                print(f"{CYAN}[{BRIGHT_MAGENTA}{idx:03d}{CYAN}]{RESET} {BRIGHT_MAGENTA}{human_readable(size):>10}{RESET} {GREEN}{path}{RESET}")
                if idx % 10 == 0:
                    print()  # Add spacing every 10 items

            # Re-display the prompt
            print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}?{CYAN}]{RESET} {YELLOW}Delete these cache directories? {BRIGHT_CYAN}[y/N]{RESET}: ", end="", flush=True)
            continue

        elif response == 'e':
            # Export to file
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            export_file = f"cache_list_{timestamp}.txt"
            try:
                with open(export_file, 'w') as f:
                    f.write("LazyScan Cache Directory Report\n")
                    f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Total cache size: {human_readable(total_size)}\n")
                    f.write(f"Total directories: {len(cache_items)}\n")
                    f.write("=" * 80 + "\n\n")

                    for idx, (path, size) in enumerate(cache_items, 1):
                        f.write(f"{idx:3d}. {human_readable(size):>10} - {path}\n")

                print(f"\n{BOLD}{CYAN}[{GREEN}✓{CYAN}]{RESET} {GREEN}Cache list exported to: {BRIGHT_CYAN}{export_file}{RESET}")
            except Exception as e:
                print(f"\n{BOLD}{CYAN}[{RED}!{CYAN}]{RESET} {RED}Error exporting: {str(e)}{RESET}")

            # Re-display the prompt
            print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}?{CYAN}]{RESET} {YELLOW}Delete these cache directories? {BRIGHT_CYAN}[y/N]{RESET}: ", end="", flush=True)
            continue

        elif response == 's':
            # Show summary by cache type
            print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}CACHE SUMMARY BY TYPE{CYAN}]{RESET}\n")

            # Categorize cache items
            categories = {
                'Browser Caches': [],
                'Development (Xcode/npm)': [],
                'System/App Caches': [],
                'Downloads (DMG/PKG)': [],
                'Logs & Diagnostics': [],
                'iOS Backups': [],
                'Temporary Files': [],
                'Other': []
            }

            for path, size in cache_items:
                path_lower = path.lower()
                if any(browser in path_lower for browser in ['chrome', 'firefox', 'safari', 'browser']):
                    categories['Browser Caches'].append((path, size))
                elif any(dev in path_lower for dev in ['xcode', 'deriveddata', 'npm', 'node_modules', 'cocoapods']):
                    categories['Development (Xcode/npm)'].append((path, size))
                elif path.endswith('.dmg') or path.endswith('.pkg'):
                    categories['Downloads (DMG/PKG)'].append((path, size))
                elif any(log in path_lower for log in ['log', 'crashreporter', 'diagnostic']):
                    categories['Logs & Diagnostics'].append((path, size))
                elif 'mobilesync' in path_lower or 'backup' in path_lower:
                    categories['iOS Backups'].append((path, size))
                elif 'tmp' in path_lower or 'temp' in path_lower:
                    categories['Temporary Files'].append((path, size))
                elif 'cache' in path_lower:
                    categories['System/App Caches'].append((path, size))
                else:
                    categories['Other'].append((path, size))

            # Display summary
            for category, items in categories.items():
                if items:
                    total_cat_size = sum(size for _, size in items)
                    print(f"{BRIGHT_CYAN}{category}:{RESET}")
                    print(f"  {YELLOW}Count:{RESET} {len(items)} items")
                    print(f"  {YELLOW}Size:{RESET} {BRIGHT_MAGENTA}{human_readable(total_cat_size)}{RESET}")
                    print()

            # Re-display the prompt
            print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}?{CYAN}]{RESET} {YELLOW}Delete these cache directories? {BRIGHT_CYAN}[y/N]{RESET}: ", end="", flush=True)
            continue

        elif response == 'y':
            break
        else:
            print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}Cache cleanup aborted.{RESET}")
            return 0

    # Delete cache directories with enhanced error handling
    print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}►{CYAN}]{RESET} {BRIGHT_CYAN}INITIATING CACHE PURGE SEQUENCE...{RESET}\n")

    freed_bytes = 0
    errors = 0
    skipped_items = []
    success_items = []
    error_details = []

    # Use Knight Rider animation
    knight_rider_animation('Preparing cleanup...', colors=colors)

    for idx, (path, size) in enumerate(cache_items):
        # Display current item being processed
        display_path = path
        if len(path) > 45:
            display_path = "..." + path[-42:]

        # Clear animation and show current item
        sys.stdout.write("\r" + " " * 100 + "\r")
        sys.stdout.write(f"{CYAN}[{idx + 1}/{len(cache_items)}]{RESET} Processing: {YELLOW}{display_path}{RESET}")
        sys.stdout.flush()

        # Use secure deletion with comprehensive safety checks
        try:
            # Use secure_delete for safe removal with backups and audit trails
            result = secure_delete([path], f"macOS Cache Cleanup - {os.path.basename(path)}")

            if result.success:
                freed_bytes += size
                success_items.append((path, size))
            else:
                errors += 1
                error_msg = result.error or "Unknown error during secure deletion"
                error_details.append((path, error_msg))
                if "in use" in error_msg.lower() or "busy" in error_msg.lower():
                    skipped_items.append((path, size, "in use"))

        except Exception as e:
            errors += 1
            error_details.append((path, f"Secure deletion failed: {str(e)}"))

    # Clear the status line
    sys.stdout.write("\r" + " " * 100 + "\r")
    sys.stdout.flush()

    # Display detailed results
    print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}✓{CYAN}]{RESET} {BRIGHT_CYAN}CACHE PURGE COMPLETE{RESET}")
    print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Space reclaimed:{RESET} {BRIGHT_MAGENTA}{human_readable(freed_bytes)}{RESET}")
    print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Items successfully cleaned:{RESET} {BRIGHT_CYAN}{len(success_items)}{RESET}")

    # Log successes if verbose
    if len(success_items) > 0 and len(success_items) <= 10:
        print(f"\n{BOLD}{CYAN}[{GREEN}SUCCESS LOG{CYAN}]{RESET}")
        for path, size in success_items[:10]:
            short_path = path.replace(os.path.expanduser('~'), '~')
            if len(short_path) > 60:
                short_path = '...' + short_path[-57:]
            print(f"  {GREEN}✓{RESET} {short_path} ({human_readable(size)})")

    # Show errors with details
    if errors > 0:
        print(f"\n{BOLD}{CYAN}[{RED}ERROR LOG{CYAN}]{RESET} {RED}Failed to clean {errors} items:{RESET}")
        for path, error_msg in error_details[:5]:  # Show first 5 errors
            short_path = path.replace(os.path.expanduser('~'), '~')
            if len(short_path) > 50:
                short_path = '...' + short_path[-47:]
            print(f"  {RED}✗{RESET} {short_path}")
            print(f"    {YELLOW}→ {error_msg}{RESET}")
        if len(error_details) > 5:
            print(f"  {YELLOW}...and {len(error_details) - 5} more errors{RESET}")

    # Show skipped items summary
    if skipped_items:
        print(f"\n{BOLD}{CYAN}[{YELLOW}SKIPPED{CYAN}]{RESET} {YELLOW}Skipped {len(skipped_items)} items (in use or locked){RESET}")

    print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}■{CYAN}]{RESET} {GREEN}Cache cleanup completed successfully.{RESET}")

    return freed_bytes


def scan_application_cache(app_name, app_paths, colors, check_path=None):
    """Generic function to scan application cache for cleanable files.

    Args:
        app_name: Display name of the application
        app_paths: List of glob patterns for cache directories
        colors: Tuple of color codes (CYAN, MAGENTA, YELLOW, RESET, BOLD)
        check_path: Optional path to check if app is installed

    Returns:
        Total bytes freed if cleaning was performed, 0 otherwise
    """
    CYAN, MAGENTA, YELLOW, RESET, BOLD = colors
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_MAGENTA = '\033[95m'
    GREEN = '\033[92m'
    RED = '\033[91m'

    print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}{app_name.upper()} SCANNER{CYAN}]{RESET} {YELLOW}Analyzing {app_name} cache...{RESET}")
    print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}▓▒░{CYAN}]{RESET} {BRIGHT_CYAN}Scanning {app_name}-specific cache and temporary files...{RESET}\n")

    # Check if app is installed (if check_path provided)
    if check_path and not os.path.exists(os.path.expanduser(check_path)):
        print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}{app_name} is not installed or cache folder not found.{RESET}")
        return 0

    # Collect cache items
    cache_items = []
    total_size = 0

    for pattern in app_paths:
        try:
            for path in glob.glob(pattern):
                try:
                    if os.path.isfile(path):
                        size = os.path.getsize(path)
                        cache_items.append((path, size, 'file'))
                        total_size += size
                    elif os.path.isdir(path):
                        # Calculate directory size
                        dir_size = 0
                        for root, dirs, files in os.walk(path):
                            for f in files:
                                try:
                                    dir_size += os.path.getsize(os.path.join(root, f))
                                except (OSError, PermissionError):
                                    pass
                        if dir_size > 0:
                            cache_items.append((path, dir_size, 'dir'))
                            total_size += dir_size
                except (OSError, PermissionError):
                    continue
        except Exception:
            continue

    if not cache_items:
        print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}No {app_name} cache files found or accessible.{RESET}")
        return 0

    # Sort by size (largest first)
    cache_items.sort(key=lambda x: x[1], reverse=True)

    # Display results
    print(f"{BOLD}{MAGENTA}┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓{RESET}")
    print(f"{BOLD}{MAGENTA}┃ {YELLOW}{app_name.upper()} CACHE ANALYSIS {CYAN}:: {BRIGHT_MAGENTA}TOTAL: {BRIGHT_CYAN}{human_readable(total_size):<10}{MAGENTA} ┃{RESET}")
    print(f"{BOLD}{MAGENTA}┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛{RESET}")

    print(f"\n{BOLD}{CYAN}[{YELLOW}CACHE ITEMS FOUND{CYAN}]{RESET} {GREEN}({len(cache_items)} items){RESET}")
    print(f"{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}\n")

    # Show top items (max 15)
    for idx, (path, size, item_type) in enumerate(cache_items[:15], 1):
        # Shorten path for display
        display_path = path.replace(os.path.expanduser('~'), '~')
        if len(display_path) > 60:
            display_path = '...' + display_path[-57:]

        icon = '📁' if item_type == 'dir' else '📄'
        print(f"{CYAN}[{BRIGHT_MAGENTA}{idx:02d}{CYAN}]{RESET} {icon} {human_readable(size):>10} {YELLOW}{display_path}{RESET}")

    if len(cache_items) > 15:
        print(f"\n{CYAN}[{YELLOW}...{CYAN}]{RESET} {YELLOW}And {len(cache_items) - 15} more items{RESET}")

    # Show total and ask for confirmation
    print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}SUMMARY{CYAN}]{RESET}")
    print(f"  {YELLOW}Total items:{RESET} {BRIGHT_CYAN}{len(cache_items)}{RESET}")
    print(f"  {YELLOW}Total size:{RESET} {BRIGHT_MAGENTA}{human_readable(total_size)}{RESET}")

    print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}?{CYAN}]{RESET} {YELLOW}Delete all {app_name} cache items? {BRIGHT_CYAN}[y/N]{RESET}: ", end="", flush=True)

    try:
        response = input().strip().lower()
    except KeyboardInterrupt:
        print(f"\n{BOLD}{CYAN}[{RED}X{CYAN}]{RESET} {RED}Operation cancelled.{RESET}")
        return 0

    if response != 'y':
        print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}{app_name} cleanup aborted.{RESET}")
        return 0

    # Clean cache
    print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}►{CYAN}]{RESET} {BRIGHT_CYAN}CLEANING {app_name.upper()} CACHE...{RESET}\n")

    knight_rider_animation(f'Purging {app_name} cache...', colors=colors)

    freed_bytes = 0
    errors = 0

    for path, size, item_type in cache_items:
        try:
            # Use secure deletion for safe removal with backups and audit trails
            result = secure_delete([path], f"{app_name} Cache Cleanup - {os.path.basename(path)}")

            if result.success:
                freed_bytes += size
            else:
                errors += 1
        except Exception:
            errors += 1

    # Clear animation
    sys.stdout.write("\r" + " " * 100 + "\r")
    sys.stdout.flush()

    # Display results
    print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}✓{CYAN}]{RESET} {BRIGHT_CYAN}{app_name.upper()} CACHE CLEANED{RESET}")
    print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Space reclaimed:{RESET} {BRIGHT_MAGENTA}{human_readable(freed_bytes)}{RESET}")
    print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Items cleaned:{RESET} {BRIGHT_CYAN}{len(cache_items) - errors}{RESET}")

    if errors > 0:
        print(f"{BOLD}{CYAN}[{RED}!{CYAN}]{RESET} {RED}Failed to clean {errors} items (permission denied){RESET}")

    print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}■{CYAN}]{RESET} {GREEN}{app_name} cleanup completed successfully.{RESET}")

    return freed_bytes


def handle_chrome_discovery(args):
    """Handle the discovery and processing of Chrome cache using the new helper."""
    if sys.platform != 'darwin':
        print("\nError: --chrome option is only available on macOS.")
        return

    # Setup colors
    CYAN = '\033[36m'
    BRIGHT_CYAN = '\033[96m'
    MAGENTA = '\033[35m'
    BRIGHT_MAGENTA = '\033[95m'
    YELLOW = '\033[33m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    colors = (CYAN, MAGENTA, YELLOW, RESET, BOLD)

    print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}CHROME SCANNER{CYAN}]{RESET} {YELLOW}Discovering Chrome profiles and cache...{RESET}")

    # Get Chrome cache report
    report = scan_chrome_cache_helper(include_profiles=True)

    if not report["installed"]:
        print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}Chrome is not installed or Application Support folder not found.{RESET}")
        return

    # Display overview
    print(f"\n{BOLD}{MAGENTA}┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓{RESET}")
    print(f"{BOLD}{MAGENTA}┃ {YELLOW}CHROME CACHE ANALYSIS {CYAN}:: {BRIGHT_MAGENTA}TOTAL: {BRIGHT_CYAN}{human_readable(report['total_size']):<10}{MAGENTA} ┃{RESET}")
    print(f"{BOLD}{MAGENTA}┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛{RESET}")

    # Show profile information
    if report['profiles']:
        print(f"\n{BOLD}{CYAN}[{YELLOW}PROFILES{CYAN}]{RESET} {GREEN}Found {len(report['profiles'])} Chrome profiles{RESET}")
        for profile in report['profiles'][:5]:  # Show max 5 profiles
            print(f"  {CYAN}•{RESET} {profile['name']}: {BRIGHT_MAGENTA}{human_readable(profile['total_size'])}{RESET}")
        if len(report['profiles']) > 5:
            print(f"  {CYAN}...and {len(report['profiles']) - 5} more{RESET}")

    # Display safe-to-delete categories
    print(f"\n{BOLD}{CYAN}[{GREEN}SAFE TO DELETE{CYAN}]{RESET} {GREEN}({human_readable(report['safe_size'])}){RESET}")
    print(f"{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")

    safe_categories = {}
    idx = 1
    for category_name, items in report['categories']['safe'].items():
        if items:
            category_size = sum(size for _, size, _ in items)
            safe_categories[str(idx)] = (category_name, items, category_size)
            print(f"\n{CYAN}[{idx}]{RESET} {BRIGHT_CYAN}{category_name}:{RESET} {BRIGHT_MAGENTA}{human_readable(category_size)}{RESET}")
            # Show top 3 items
            for path, size, _ in sorted(items, key=lambda x: x[1], reverse=True)[:3]:
                display_path = path.replace(report["chrome_base"] + '/', '')
                if len(display_path) > 55:
                    display_path = '...' + display_path[-52:]
                print(f"  {GREEN}→{RESET} {human_readable(size):>10} {YELLOW}{display_path}{RESET}")
            if len(items) > 3:
                print(f"  {CYAN}...and {len(items) - 3} more items{RESET}")
            idx += 1

    # Show preserved data
    if report['unsafe_size'] > 0:
        print(f"\n{BOLD}{CYAN}[{RED}PRESERVE{CYAN}]{RESET} {RED}({human_readable(report['unsafe_size'])}){RESET}")
        print(f"{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        for category_name, items in report['categories']['unsafe'].items():
            if items:
                category_size = sum(size for _, size, _ in items)
                print(f"  {RED}{category_name}:{RESET} {BRIGHT_MAGENTA}{human_readable(category_size)}{RESET} {YELLOW}(User data){RESET}")

    # Interactive selection
    print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}?{CYAN}]{RESET} {YELLOW}Select items to clean:{RESET}")
    print(f"  {CYAN}a{RESET} - All safe categories")
    print(f"  {CYAN}q{RESET} - Quit without cleaning")
    if idx > 1:
        print(f"  {CYAN}1-{idx - 1}{RESET} - Individual categories (comma-separated)")

    selection = input(f"\n{YELLOW}Your choice:{RESET} ").strip().lower()

    if selection == 'q':
        print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}Chrome cleanup cancelled.{RESET}")
        return

    # Determine items to clean
    items_to_clean = []
    if selection == 'a':
        for category_name, items in report['categories']['safe'].items():
            items_to_clean.extend(items)
    else:
        try:
            for idx in selection.split(','):
                idx = idx.strip()
                if idx in safe_categories:
                    _, items, _ = safe_categories[idx]
                    items_to_clean.extend(items)
        except (ValueError, KeyError):
            print(f"{BOLD}{CYAN}[{RED}!{CYAN}]{RESET} {RED}Invalid selection.{RESET}")
            return

    if not items_to_clean:
        print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}No items selected.{RESET}")
        return

    # Calculate total to clean
    total_to_clean = sum(size for _, size, _ in items_to_clean)

    # Confirm
    print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}?{CYAN}]{RESET} {YELLOW}Delete {BRIGHT_CYAN}{len(items_to_clean)}{YELLOW} items ({BRIGHT_MAGENTA}{human_readable(total_to_clean)}{YELLOW})? {BRIGHT_CYAN}[y/N]{RESET}: ", end="", flush=True)

    if input().strip().lower() != 'y':
        print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}Chrome cleanup cancelled.{RESET}")
        return

    # Clean
    print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}►{CYAN}]{RESET} {BRIGHT_CYAN}CLEANING CHROME CACHE...{RESET}")

    knight_rider_animation('Purging Chrome cache...', colors=colors)

    freed_bytes = 0
    errors = 0

    for path, size, item_type in items_to_clean:
        try:
            if item_type == 'dir' and os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            elif item_type == 'file' and os.path.isfile(path):
                os.remove(path)
            freed_bytes += size
        except (OSError, PermissionError):
            errors += 1

    # Clear animation
    sys.stdout.write("\r" + " " * 100 + "\r")
    sys.stdout.flush()

    # Results
    print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}✓{CYAN}]{RESET} {BRIGHT_CYAN}CHROME CACHE CLEANED{RESET}")
    print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Space reclaimed:{RESET} {BRIGHT_MAGENTA}{human_readable(freed_bytes)}{RESET}")
    print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}→{CYAN}]{RESET} {YELLOW}Items cleaned:{RESET} {BRIGHT_CYAN}{len(items_to_clean) - errors}{RESET}")

    if errors > 0:
        print(f"{BOLD}{CYAN}[{RED}!{CYAN}]{RESET} {RED}Failed to clean {errors} items{RESET}")

    print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}■{CYAN}]{RESET} {GREEN}Chrome cleanup completed!{RESET}")


def knight_rider_animation(message, iterations=3, animation_chars="▮▯▯", delay=0.07, colors=None):
    """Display a Knight Rider style animation while performing a task"""
    # Default colors if none provided
    if colors is None:
        # Neutral colors for fallback
        CYAN = MAGENTA = YELLOW = RESET = BOLD = ''
    else:
        CYAN, MAGENTA, YELLOW, RESET, BOLD = colors

    animation_width = 10
    for _ in range(iterations):
        # Knight Rider animation going right
        for i in range(animation_width):
            anim = "▯" * i + animation_chars + "▯" * (animation_width - i - len(animation_chars))
            sys.stdout.write(f"\r{BOLD}{CYAN}[{MAGENTA}{anim}{CYAN}]{RESET} {YELLOW}{message}{RESET}")
            sys.stdout.flush()
            time.sleep(delay)

        # Knight Rider animation going left
        for i in range(animation_width - 1, -1, -1):
            anim = "▯" * i + animation_chars + "▯" * (animation_width - i - len(animation_chars))
            sys.stdout.write(f"\r{BOLD}{CYAN}[{MAGENTA}{anim}{CYAN}]{RESET} {YELLOW}{message}{RESET}")
            sys.stdout.flush()
            time.sleep(delay)

    # Clear the animation line when done
    sys.stdout.write("\r" + " " * (len(message) + 30) + "\r")
    sys.stdout.flush()


# Funny messages for the scan
FUNNY_MESSAGES = [
    "Converting caffeine into code...",
    "Teaching AI to count without using fingers...",
    "Preparing to blame your downloads folder...",
    "Calculating how many cat videos you have...",
    "Checking if you've actually cleaned up those temp files...",
    "Looking for your 'definitely not important' folder...",
    "Finding where all those 'I'll sort this later' files went...",
    "Locating your digital hoarding evidence...",
    "Discovering what's actually filling up your drive...",
    "Searching for those 'I might need this someday' files...",
]


def get_disk_usage(path='/'):
    """Get disk usage statistics for a given path.

    Returns a tuple of (total, used, free, formatted_string) where:
    - total: Total disk space in bytes
    - used: Used disk space in bytes
    - free: Free disk space in bytes
    - formatted_string: Colored human-readable string showing usage
    """
    try:
        # Get disk usage statistics
        usage = shutil.disk_usage(path)
        total = usage.total
        used = usage.used
        free = usage.free

        # Calculate percentage used
        percent_used = (used / total) * 100 if total > 0 else 0

        # Determine if we're in a terminal for color support
        use_color = sys.stdout.isatty()

        if use_color:
            # Define colors based on usage percentage
            if percent_used >= 90:
                # Critical - Red
                color = '\033[91m'  # Bright red
            elif percent_used >= 70:
                # Warning - Yellow
                color = '\033[93m'  # Bright yellow
            else:
                # Good - Green
                color = '\033[92m'  # Bright green

            # Cyberpunk color scheme elements
            CYAN = '\033[36m'
            BRIGHT_CYAN = '\033[96m'
            BRIGHT_MAGENTA = '\033[95m'
            RESET = '\033[0m'
            BOLD = '\033[1m'

            # Format the string with colors
            formatted_string = (
                f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}DISK{CYAN}]{RESET} "
                f"Total: {BRIGHT_CYAN}{human_readable(total)}{RESET} | "
                f"Used: {color}{human_readable(used)}{RESET} ({color}{percent_used:.1f}%{RESET}) | "
                f"Free: {BRIGHT_CYAN}{human_readable(free)}{RESET}"
            )
        else:
            # No color version
            formatted_string = (
                f"[DISK] Total: {human_readable(total)} | "
                f"Used: {human_readable(used)} ({percent_used:.1f}%) | "
                f"Free: {human_readable(free)}"
            )

        return total, used, free, formatted_string

    except Exception as e:
        # Handle any errors (e.g., permission denied, invalid path)
        error_msg = f"Error getting disk usage: {str(e)}"
        return 0, 0, 0, error_msg


def select_directory():
    """Let the user choose a directory from stdin."""
    cwd = os.getcwd()
    dirs = ['.'] + sorted([d for d in os.listdir(cwd) if os.path.isdir(os.path.join(cwd, d))])
    print("Select directory to scan:")
    for idx, d in enumerate(dirs, start=1):
        print(f"  {idx}. {d}")
    print("  0. Enter custom path")
    while True:
        choice = input(f"Choice [0-{len(dirs)}]: ").strip()
        if not choice.isdigit():
            print("Please enter a number.")
            continue
        n = int(choice)
        if n == 0:
            custom = input("Enter path to scan: ").strip()
            return custom
        if 1 <= n <= len(dirs):
            return dirs[n-1]
        print(f"Invalid choice: {choice}")


def handle_unreal_discovery(args):
    """Handle the discovery and processing of Unreal projects."""
    from helpers.unreal_launcher import get_unreal_projects
    import sys
    import random
    import threading

    # Define colors for styled output
    CYAN = '\033[36m'
    BRIGHT_CYAN = '\033[96m'
    MAGENTA = '\033[35m'
    BRIGHT_MAGENTA = '\033[95m'
    YELLOW = '\033[33m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

    # Setup color pack for animation
    colors = (CYAN, MAGENTA, YELLOW, RESET, BOLD)

    # Discover Unreal projects using the launcher and custom paths
    print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}UNREAL ENGINE SCANNER{CYAN}]{RESET} {YELLOW}Searching for Unreal Engine projects...{RESET}")

    # Select a random funny message
    funny_msg = random.choice(FUNNY_MESSAGES)

    # Show animation while discovering projects
    projects = []
    discovery_done = False

    def discover_projects():
        nonlocal projects, discovery_done
        projects = get_unreal_projects()
        discovery_done = True

    # Run discovery in a thread
    discovery_thread = threading.Thread(target=discover_projects)
    discovery_thread.start()

    # Show animation while discovering
    while discovery_thread.is_alive():
        knight_rider_animation(funny_msg, iterations=1, colors=colors)
        if not discovery_thread.is_alive():
            break

    discovery_thread.join()

    if not projects:
        print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}No Unreal Engine projects found.{RESET}")
        return

    print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}✓{CYAN}]{RESET} {GREEN}Found {len(projects)} Unreal Engine projects.{RESET}")

    # Prompt user to select projects
    if sys.stdin.isatty():
        selected_projects = prompt_unity_project_selection(projects)
    else:
        print("Non-interactive terminal. Using all projects.")
        selected_projects = projects

    if not selected_projects:
        print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}No Unreal projects selected.{RESET}")
        return

    print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}UNREAL SCANNER{CYAN}]{RESET} {YELLOW}Generating Unreal Project Reports...{RESET}")

    total_size = 0
    total_freed = 0

    for project in selected_projects:
        report = generate_unreal_project_report(project['path'])
        total_size += report['total_size']

        # Display the report
        print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}PROJECT{CYAN}]{RESET} {YELLOW}{report['name']}{RESET}")
        print(f"{CYAN}Path:{RESET} {GREEN}{report['path']}{RESET}")
        print(f"{CYAN}Total Cache Size:{RESET} {BRIGHT_MAGENTA}{human_readable(report['total_size'])}{RESET}")

        # Display individual cache directories
        print(f"\n{CYAN}Cache Directories:{RESET}")
        for cache_name, cache_info in report['cache_dirs'].items():
            if cache_info['exists']:
                print(f"  {GREEN}✓{RESET} {cache_name}: {BRIGHT_MAGENTA}{human_readable(cache_info['size'])}{RESET}")
            else:
                print(f"  {YELLOW}✗{RESET} {cache_name}: {YELLOW}Not found{RESET}")

        # Ask if the user wants to clean caches if in interactive mode and caches exist
        if sys.stdin.isatty() and report['total_size'] > 0:
            print(f"\n{CYAN}Would you like to clean cache directories for this project?{RESET}")
            response = input("Clean caches? (y/N): ").strip().lower()

            if response == 'y':
                # Options for clearing specific cache types
                print("\nChoose which cache directories to clear:")
                print("  a - All")
                print("  i - Intermediate")
                print("  s - Saved/Logs")
                print("  c - Saved/Crashes")
                print("  d - DerivedDataCache")
                print("  b - Binaries")
                print("  n - None (skip)")

                choices = input("Enter choices separated by commas (e.g., i,s,c): ").strip().lower().split(",")

                # Skip if 'n' is selected
                if 'n' in choices:
                    print(f"{YELLOW}Skipping cache cleaning for this project.{RESET}")
                    continue

                # Determine directories to clear
                directories_to_clear = []
                if 'a' in choices:
                    directories_to_clear = [name for name, info in report['cache_dirs'].items() if info['exists']]
                else:
                    available_choices = {
                        'i': 'Intermediate',
                        's': 'Saved/Logs',
                        'c': 'Saved/Crashes',
                        'd': 'DerivedDataCache',
                        'b': 'Binaries'
                    }
                    for choice in choices:
                        if choice in available_choices and available_choices[choice] in report['cache_dirs']:
                            if report['cache_dirs'][available_choices[choice]]['exists']:
                                directories_to_clear.append(available_choices[choice])

                # Clean selected directories
                project_freed = 0
                for cache_name in directories_to_clear:
                    cache_info = report['cache_dirs'][cache_name]
                    try:
                        size_before = cache_info['size']
                        # Use secure deletion for safe removal with backups and audit trails
                        result = secure_delete([cache_info['path']], f"Unity Cache Cleanup - {cache_name}")

                        if result.success:
                            project_freed += size_before
                            print(f"  {GREEN}✓ Cleared:{RESET} {cache_name} ({BRIGHT_MAGENTA}{human_readable(size_before)}{RESET} freed)")
                        else:
                            error_msg = result.error or "Unknown error during secure deletion"
                            if "permission" in error_msg.lower():
                                print(f"  {RED}✗ Permission denied:{RESET} {cache_name}")
                            elif "not found" in error_msg.lower():
                                print(f"  {YELLOW}✗ Already deleted:{RESET} {cache_name}")
                            else:
                                print(f"  {RED}✗ Failed to clear {cache_name}:{RESET} {error_msg}")
                    except Exception as e:
                        print(f"  {RED}✗ Failed to clear {cache_name}:{RESET} {str(e)}")

                if project_freed > 0:
                    total_freed += project_freed
                    print(f"\n{GREEN}Space freed for this project:{RESET} {BRIGHT_MAGENTA}{human_readable(project_freed)}{RESET}")

    print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}SUMMARY{CYAN}]{RESET}")
    print(f"{CYAN}Total Cache Size for all selected projects:{RESET} {BRIGHT_MAGENTA}{human_readable(total_size)}{RESET}")
    if total_freed > 0:
        print(f"{GREEN}Total Space Freed:{RESET} {BRIGHT_MAGENTA}{human_readable(total_freed)}{RESET}")


def handle_unity_discovery(args):
    """Handle the discovery and processing of Unity projects."""
    handle_unity_projects_integration(args)

def handle_unity_projects_integration(args):
    """Handle the discovery of Unity projects via Unity Hub and existing methodologies."""

    if not args.no_unityhub:
        return scan_unity_project_via_hub(args, clean=args.clean)
    else:
        return default_directory_picker()

def scan_unity_project_via_hub(args, clean=False):
    """Scan Unity projects via Unity Hub and generate a report."""
    import random
    import threading

    CYAN = '\033[36m'
    BRIGHT_CYAN = '\033[96m'
    MAGENTA = '\033[35m'
    BRIGHT_MAGENTA = '\033[95m'
    YELLOW = '\033[33m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    colors = (CYAN, MAGENTA, YELLOW, RESET, BOLD)

    print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}UNITY HUB SCANNER{CYAN}]{RESET} {YELLOW}Discovering Unity projects via Unity Hub...{RESET}")

    # Select a random funny message
    funny_msg = random.choice(FUNNY_MESSAGES)

    # Show animation while discovering projects
    projects = []
    discovery_done = False

    def discover_unity_projects():
        nonlocal projects, discovery_done
        try:
            unity_hub_json_path = args.unityhub_json if args.unityhub_json else None
            projects = read_unity_hub_projects(unity_hub_json_path)
        except Exception as e:
            # Store exception to handle after animation
            projects = e
        discovery_done = True

    # Run discovery in a thread
    discovery_thread = threading.Thread(target=discover_unity_projects)
    discovery_thread.start()

    # Show animation while discovering
    while discovery_thread.is_alive():
        knight_rider_animation(funny_msg, iterations=1, colors=colors)
        if not discovery_thread.is_alive():
            break

    discovery_thread.join()

    # Check if an exception occurred
    if isinstance(projects, Exception):
        raise projects

    try:
        unity_hub_json_path = args.unityhub_json if args.unityhub_json else None

        if not projects:
            print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}No Unity projects found in Unity Hub.{RESET}")
            return

        print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}✓{CYAN}]{RESET} {GREEN}Found {len(projects)} Unity projects in Unity Hub.{RESET}")

        # Prompt user to select projects if not in clean mode or if there are multiple projects
        selected_projects = []
        if clean and not args.pick and len(projects) > 0:
            # If in clean mode and not forcing pick, assume all projects are to be cleaned
            selected_projects = projects
        else:
            selected_projects = prompt_unity_project_selection(projects)

        if not selected_projects:
            print(f"{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}No Unity projects selected. Aborting scan.{RESET}")
            return

        print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}UNITY SCANNER{CYAN}]{RESET} {YELLOW}Generating Unity Project Reports...{RESET}")

        for project in selected_projects:
            report = generate_unity_project_report(
                project['path'],
                project['name'],
                include_build=args.build_dir
            )

            # Display the report
            print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}PROJECT{CYAN}]{RESET} {YELLOW}{report['name']}{RESET}")
            print(f"{CYAN}Path:{RESET} {GREEN}{report['path']}{RESET}")
            print(f"{CYAN}Total Cache Size:{RESET} {BRIGHT_MAGENTA}{human_readable(report['total_size'])}{RESET}")

            # Display individual cache directories
            print(f"\n{CYAN}Cache Directories:{RESET}")
            for cache_name, cache_info in report['cache_dirs'].items():
                if cache_info['exists']:
                    print(f"  {GREEN}✓{RESET} {cache_name}: {BRIGHT_MAGENTA}{human_readable(cache_info['size'])}{RESET}")
                else:
                    print(f"  {YELLOW}✗{RESET} {cache_name}: {YELLOW}Not found{RESET}")

            print()

            # Ask if the user wants to clear cache directories
            # Options for clearing specific cache types
            print("Choose which cache directories to clear:")
            print("  a - All")
            print("  l - Library")
            print("  t - Temp")
            print("  o - obj")
            print("  g - Logs")
            choices = input("Enter choices separated by commas (e.g., a,l,t): ").strip().lower().split(",")

            # Determine directories to clear
            directories_to_clear = []
            if 'a' in choices:
                directories_to_clear = report['cache_dirs'].keys()
            else:
                available_choices = {'l': 'Library', 't': 'Temp', 'o': 'obj', 'g': 'Logs'}
                for choice in choices:
                    if choice in available_choices:
                        directories_to_clear.append(available_choices[choice])

            for cache_name in directories_to_clear:
                cache_info = report['cache_dirs'][cache_name]
                if cache_info['exists']:
                    try:
                        # Use secure deletion for safe removal with backups and audit trails
                        result = secure_delete([cache_info['path']], f"Unreal Cache Cleanup - {cache_name}")

                        if result.success:
                            print(f"{GREEN}✓ Cleared: {cache_name}{RESET}")
                        else:
                            error_msg = result.error or "Unknown error during secure deletion"
                            print(f"{RED}✗ Failed to clear {cache_name}: {error_msg}{RESET}")
                    except Exception as e:
                        print(f"{RED}✗ Failed to clear {cache_name}: {e}{RESET}")

            print("Selected cache directories have been processed.")


































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































    except FileNotFoundError:
        print(f"{BOLD}{CYAN}[{RED}ERROR{CYAN}]{RESET} {RED}Unity Hub preferences file not found. Ensure Unity Hub is installed and has been run at least once.{RESET}")
    except Exception as e:
        print(f"{BOLD}{CYAN}[{RED}ERROR{CYAN}]{RESET} {RED}An error occurred during Unity Hub project discovery: {e}{RESET}")

def default_directory_picker():
    """Placeholder for default directory picking logic."""
    print(f"\n{BOLD}{CYAN}[{YELLOW}!{CYAN}]{RESET} {YELLOW}Unity Hub discovery suppressed. Implement default directory picker here.{RESET}")
    return None


def show_logo():
    """Display the lazyscan cyberpunk-style logo"""
    # Define ANSI color codes
    CYAN = '\033[36m'
    BRIGHT_CYAN = '\033[96m'
    MAGENTA = '\033[35m'
    BRIGHT_MAGENTA = '\033[95m'
    YELLOW = '\033[33m'
    GREEN = '\033[32m'
    BLUE = '\033[34m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

    # Clear, modern ASCII art that clearly says "LAZY SCAN"
    logo_lines = [
        f"{CYAN}██{MAGENTA}      {BRIGHT_CYAN}█████{YELLOW}   {GREEN}███{BLUE}   {MAGENTA}██{BRIGHT_CYAN}     {YELLOW}███{GREEN}   {BLUE}██████{MAGENTA}    {BRIGHT_CYAN}█████{YELLOW}   {GREEN}██{BLUE}    {MAGENTA}██{BRIGHT_CYAN}",
        f"{CYAN}██{MAGENTA}      {BRIGHT_CYAN}██{YELLOW}  {GREEN}██{BLUE}  {MAGENTA}██{BRIGHT_CYAN} ██{YELLOW}  {GREEN}██{BLUE} {MAGENTA}██{BRIGHT_CYAN}    {YELLOW}██{GREEN} ██{BLUE}  {MAGENTA}██{BRIGHT_CYAN}  {YELLOW}██{GREEN}  {BLUE}██{MAGENTA}  {BRIGHT_CYAN}██{YELLOW} {GREEN}██{BLUE}   {MAGENTA}██{BRIGHT_CYAN}",
        f"{CYAN}██{MAGENTA}      {BRIGHT_CYAN}██{YELLOW}  {GREEN}██{BLUE}  {MAGENTA}██{BRIGHT_CYAN}███{YELLOW}   {GREEN}██{BLUE} {MAGENTA}██{BRIGHT_CYAN}    {YELLOW}██{GREEN}  {BLUE}█████{MAGENTA}   {BRIGHT_CYAN}█████{YELLOW}   {GREEN}██{BLUE}  {MAGENTA}██{BRIGHT_CYAN} ",
        f"{CYAN}██{MAGENTA}      {BRIGHT_CYAN}██{YELLOW}  {GREEN}██{BLUE}  {MAGENTA}██{BRIGHT_CYAN} ██{YELLOW}  {GREEN}██{BLUE} {MAGENTA}██{BRIGHT_CYAN}    {YELLOW}██{GREEN}    {BLUE}██{MAGENTA}    {BRIGHT_CYAN}██{YELLOW}  {GREEN}██{BLUE}  {MAGENTA}██{BRIGHT_CYAN} {YELLOW}██{GREEN} ",
        f"{CYAN}███████{MAGENTA} {BRIGHT_CYAN}█████{YELLOW}   {GREEN}██{BLUE}  {MAGENTA}██{BRIGHT_CYAN} {YELLOW} {GREEN}█████{BLUE}  {MAGENTA}██████{BRIGHT_CYAN} {YELLOW}██{GREEN}   {BLUE}██{MAGENTA}  {BRIGHT_CYAN}██{YELLOW}   {GREEN}██{BLUE} {MAGENTA}███████{BRIGHT_CYAN}",
    ]

    for line in logo_lines:
        print(line)

    print(f"\n{BOLD}{CYAN}[{MAGENTA}*{CYAN}]{RESET} {YELLOW}The next-gen tool for the {GREEN}lazy{YELLOW} developer who wants results {GREEN}fast{RESET}")
    print(f"{BOLD}{CYAN}[{MAGENTA}*{CYAN}]{RESET} {BLUE}Created by {MAGENTA}TheLazyIndianTechie{RESET} {YELLOW}// {GREEN}v{__version__}{RESET}\n")


def show_disclaimer():
    """Display the disclaimer for using lazyscan"""
    # Define ANSI color codes for the disclaimer
    CYAN = '\033[36m'
    BRIGHT_CYAN = '\033[96m'
    MAGENTA = '\033[35m'
    BRIGHT_MAGENTA = '\033[95m'
    YELLOW = '\033[33m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

    print(f"{BOLD}{MAGENTA}╔═══════════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{MAGENTA}║{BRIGHT_CYAN}                             DISCLAIMER                                 {MAGENTA}║{RESET}")
    print(f"{BOLD}{MAGENTA}╠═══════════════════════════════════════════════════════════════════════╣{RESET}")
    print(f"{BOLD}{MAGENTA}║{RESET} {YELLOW}This tool is provided AS-IS for disk space analysis and cache{RESET}         {MAGENTA}║{RESET}")
    print(f"{BOLD}{MAGENTA}║{RESET} {YELLOW}management. By using this tool, you acknowledge that:{RESET}                  {MAGENTA}║{RESET}")
    print(f"{BOLD}{MAGENTA}║{RESET}                                                                        {MAGENTA}║{RESET}")
    print(f"{BOLD}{MAGENTA}║{RESET} {CYAN}• Deleting cache files may affect application performance{RESET}              {MAGENTA}║{RESET}")
    print(f"{BOLD}{MAGENTA}║{RESET} {CYAN}• Some applications may need to rebuild caches after deletion{RESET}          {MAGENTA}║{RESET}")
    print(f"{BOLD}{MAGENTA}║{RESET} {CYAN}• Always verify files before deletion{RESET}                                  {MAGENTA}║{RESET}")
    print(f"{BOLD}{MAGENTA}║{RESET} {CYAN}• The author is not responsible for any data loss{RESET}                      {MAGENTA}║{RESET}")
    print(f"{BOLD}{MAGENTA}║{RESET}                                                                        {MAGENTA}║{RESET}")
    print(f"{BOLD}{MAGENTA}║{RESET} {RED}⚠️  USE AT YOUR OWN RISK ⚠️{RESET}                                             {MAGENTA}║{RESET}")
    print(f"{BOLD}{MAGENTA}╚═══════════════════════════════════════════════════════════════════════╝{RESET}")
    print()

def main():
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
    parser.add_argument('-n', '--top', type=int, default=20,
                        help='number of top files to display (default: 20)')
    parser.add_argument('-w', '--width', type=int, default=40,
                        help='bar width in characters (default: 40)')
    parser.add_argument('-i', '--interactive', action='store_true',
                        help='prompt to choose directory (for the truly lazy)')
    parser.add_argument('--no-logo', action='store_true',
                        help='hide the lazyscan logo')
    parser.add_argument('--macos', action='store_true',
                        help='clean macOS cache directories (can be used with or without scanning)')
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
    parser.add_argument('path', nargs='?', default=None,
                        help='directory path to scan (default: current directory)')
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}',
                        help='show version number and exit')
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

    args = parser.parse_args()

    if not args.no_logo:
        show_logo()
        # Check and display disclaimer only if not acknowledged
        if not has_seen_disclaimer():
            show_disclaimer()
            input('Press Enter to acknowledge the disclaimer and continue...')
            mark_disclaimer_acknowledged()

    # Initialize security system
    security_enabled = initialize_security_system()

    # Handle security and recovery options
    if args.recovery:
        print("\n=== Recovery System ===")
        stats = get_recovery_stats()
        print(f"Total recoverable operations: {stats.get('total_operations', 0)}")
        print(f"Successful recoveries: {stats.get('successful_recoveries', 0)}")
        print(f"Failed recoveries: {stats.get('failed_recoveries', 0)}")
        print(f"Total files backed up: {stats.get('total_files_backed_up', 0)}")
        print(f"Total backup size: {stats.get('total_backup_size_mb', 0):.2f} MB")

        from helpers.recovery import list_recent_operations
        recent_ops = list_recent_operations(7)
        if recent_ops:
            print("\nRecent operations (last 7 days):")
            for op in recent_ops[:10]:  # Show last 10
                print(f"  {op['timestamp']}: {op['operation_type']} - {op['files_affected']} files")
        else:
            print("\nNo recent operations found.")
        return

    if args.audit_logs:
        from helpers.audit import get_audit_summary
        summary = get_audit_summary(24)  # Last 24 hours
        print(f"\n📋 Audit Log Summary (Last 24 Hours):")
        print(f"   Total Events: {summary.get('total_events', 0)}")
        print(f"   Scan Operations: {summary.get('scan_operations', 0)}")
        print(f"   Delete Operations: {summary.get('delete_operations', 0)}")
        print(f"   Security Events: {summary.get('security_events', 0)}")
        print(f"   Errors: {summary.get('errors', 0)}")
        if summary.get('session_id'):
            print(f"   Session ID: {summary['session_id']}")
        if summary.get('total_events', 0) == 0:
            print("   No audit events found in the last 24 hours.")
        return

    if args.recovery_stats:
        stats = get_recovery_stats()
        print(f"\n📊 Recovery System Statistics:")
        print(f"   Recoverable Operations: {stats.get('recoverable_operations', 0)}")
        print(f"   Total Files: {stats.get('total_files_recoverable', 0):,}")
        print(f"   Total Size: {stats.get('total_size_recoverable', 0) / (1024**3):.2f} GB")
        if stats.get('oldest_operation'):
            print(f"   Oldest Operation: {stats['oldest_operation']}")
        if stats.get('newest_operation'):
            print(f"   Newest Operation: {stats['newest_operation']}")
        if not stats.get('recoverable_operations', 0):
            print("   No recovery operations available.")
        return

    # Handle Unity-specific discovery if requested
    if args.unity:
        handle_unity_discovery(args)
        return

    # Handle Unreal-specific discovery if requested
    if args.unreal:
        handle_unreal_discovery(args)
        return

    # Handle Chrome cache scanning if requested
    if args.chrome:
        # Platform guard - Chrome scanning is macOS only for now
        if sys.platform != 'darwin':
            print("\nError: --chrome option is only available on macOS.")
            sys.exit(1)

        # Setup colors
        if sys.stdout.isatty():
            colors = ('\033[36m', '\033[35m', '\033[33m', '\033[0m', '\033[1m')
        else:
            colors = ('', '', '', '', '')

        # Scan Chrome cache
        handle_chrome_discovery(args)

        # If only Chrome scanning was requested, exit
        if not args.path and not args.interactive and not args.macos:
            return

    # Handle macOS cache cleaning if requested
    if args.macos:
        # Platform guard - macOS only feature
        if sys.platform != 'darwin':
            print("\nError: --macos option is only available on macOS.")
            sys.exit(1)

        # Get disk usage before cleaning
        total_before, used_before, free_before, _ = get_disk_usage()

        # Setup colors for cache cleaning
        if sys.stdout.isatty():
            colors = ('\033[36m', '\033[35m', '\033[33m', '\033[0m', '\033[1m')  # CYAN, MAGENTA, YELLOW, RESET, BOLD
            CYAN, MAGENTA, YELLOW, RESET, BOLD = colors
            BRIGHT_CYAN = '\033[96m'
            BRIGHT_MAGENTA = '\033[95m'
            GREEN = '\033[92m'
            BLUE = '\033[94m'
        else:
            colors = ('', '', '', '', '')  # No colors for non-terminal output
            CYAN = MAGENTA = YELLOW = RESET = BOLD = BRIGHT_CYAN = BRIGHT_MAGENTA = GREEN = BLUE = ''

        # Display initial disk usage
        print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}SYSTEM STATUS{CYAN}]{RESET} {YELLOW}Current disk usage:{RESET}")
        _, _, _, usage_before_str = get_disk_usage()
        print(usage_before_str)

        # Clean macOS cache directories
        freed_bytes = clean_macos_cache(MACOS_CACHE_PATHS, colors)

        # Get disk usage after cleaning
        total_after, used_after, free_after, _ = get_disk_usage()

        # Display summary banner if space was actually freed
        if freed_bytes > 0:
            print(f"\n{BOLD}{MAGENTA}╔═══════════════════════════════════════════════════════════════════════╗{RESET}")
            print(f"{BOLD}{MAGENTA}║ {BRIGHT_CYAN}CACHE CLEANUP SUMMARY {MAGENTA}║{RESET}")
            print(f"{BOLD}{MAGENTA}╠═══════════════════════════════════════════════════════════════════════╣{RESET}")
            print(f"{BOLD}{MAGENTA}║ {YELLOW}Space Freed:{RESET} {BRIGHT_MAGENTA}{human_readable(freed_bytes):>15}{RESET}                                        {MAGENTA}║{RESET}")
            print(f"{BOLD}{MAGENTA}║ {YELLOW}Disk Used Before:{RESET} {BRIGHT_CYAN}{human_readable(used_before):>10}{RESET} ({(used_before/total_before*100):.1f}%)                        {MAGENTA}║{RESET}")
            print(f"{BOLD}{MAGENTA}║ {YELLOW}Disk Used After:{RESET}  {GREEN}{human_readable(used_after):>10}{RESET} ({(used_after/total_after*100):.1f}%)                        {MAGENTA}║{RESET}")
            print(f"{BOLD}{MAGENTA}║ {YELLOW}Free Space Gained:{RESET} {BRIGHT_MAGENTA}{human_readable(free_after - free_before):>9}{RESET}                                         {MAGENTA}║{RESET}")
            print(f"{BOLD}{MAGENTA}╚═══════════════════════════════════════════════════════════════════════╝{RESET}")

            # Display updated disk usage
            print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}SYSTEM STATUS{CYAN}]{RESET} {YELLOW}Updated disk usage:{RESET}")
            _, _, _, usage_after_str = get_disk_usage()
            print(usage_after_str)

        # If only cleaning was requested (no scan flags), exit gracefully
        if not args.path and not args.interactive:
            # User likely just wants to clean cache and exit
            print(f"\n{BOLD}{CYAN}[{BRIGHT_MAGENTA}✓{CYAN}]{RESET} {GREEN}Operation completed successfully.{RESET}")
            return

    # Setup colors for application scanning
    if sys.stdout.isatty():
        colors = ('\033[36m', '\033[35m', '\033[33m', '\033[0m', '\033[1m')
    else:
        colors = ('', '', '', '', '')

    # Track if any app-specific scanning was requested
    app_scan_requested = any([
        args.perplexity, args.dia, args.slack, args.discord, args.spotify,
        args.vscode, args.zoom, args.teams, args.firefox, args.safari
    ])

    # Handle Perplexity AI cache scanning if requested
    if args.perplexity:
        scan_application_cache('Perplexity', PERPLEXITY_PATHS, colors, check_path='~/Library/Application Support/Perplexity')

    # Handle Dia cache scanning if requested
    if args.dia:
        scan_application_cache('Dia', DIA_PATHS, colors, check_path='~/Library/Application Support/Dia')

    # Handle Slack cache scanning if requested
    if args.slack:
        scan_application_cache('Slack', SLACK_PATHS, colors, check_path='~/Library/Application Support/Slack')

    # Handle Discord cache scanning if requested
    if args.discord:
        scan_application_cache('Discord', DISCORD_PATHS, colors, check_path='~/Library/Application Support/discord')

    # Handle Spotify cache scanning if requested
    if args.spotify:
        scan_application_cache('Spotify', SPOTIFY_PATHS, colors, check_path='~/Library/Application Support/Spotify')

    # Handle VS Code cache scanning if requested
    if args.vscode:
        scan_application_cache('VS Code', VSCODE_PATHS, colors, check_path='~/Library/Application Support/Code')

    # Handle Zoom cache scanning if requested
    if args.zoom:
        scan_application_cache('Zoom', ZOOM_PATHS, colors, check_path='~/Library/Application Support/zoom.us')

    # Handle Teams cache scanning if requested
    if args.teams:
        scan_application_cache('Teams', TEAMS_PATHS, colors, check_path='~/Library/Application Support/Microsoft/Teams')

    # Handle Firefox cache cleaning if requested
    if args.firefox:
        scan_application_cache('Firefox', FIREFOX_PATHS, colors, check_path='~/Library/Application Support/Firefox')

    # Handle Safari cache cleaning if requested
    if args.safari:
        scan_application_cache('Safari', SAFARI_PATHS, colors, check_path='~/Library/Caches/com.apple.Safari')

    # If app-specific scanning was requested and no path/interactive mode, exit
    if app_scan_requested and not args.path and not args.interactive:
        return

    # Determine scan path
    if args.interactive:
        scan_path = select_directory()
    else:
        scan_path = args.path or '.'

    # Cyberpunk color scheme
    use_color = sys.stdout.isatty()
    if use_color:
        # Define cyberpunk-style color palette
        CYAN = '\033[36m'
        BRIGHT_CYAN = '\033[96m'
        MAGENTA = '\033[35m'
        BRIGHT_MAGENTA = '\033[95m'
        YELLOW = '\033[33m'
        GREEN = '\033[92m'
        BLUE = '\033[94m'
        RED = '\033[91m'
        BOLD = '\033[1m'
        RESET = '\033[0m'

        # Colors for specific elements
        BAR_COLOR = BRIGHT_CYAN
        SIZE_COLOR = BRIGHT_MAGENTA
        HEADER_COLOR = YELLOW
        PATH_COLOR = GREEN
        ACCENT_COLOR = MAGENTA
    else:
        # Fallback for non-terminal output
        CYAN = BRIGHT_CYAN = MAGENTA = BRIGHT_MAGENTA = YELLOW = GREEN = BLUE = RED = BOLD = RESET = ''
        BAR_COLOR = SIZE_COLOR = HEADER_COLOR = PATH_COLOR = ACCENT_COLOR = ''

    # Use full block character for the bar
    BLOCK = '█'

    # Initialize terminal and progress display
    term_width = os.get_terminal_size().columns if sys.stdout.isatty() else 80
    use_progress = sys.stdout.isatty()  # Only use progress display on actual terminals

    # First pass to count total files with Knight Rider animation
    total_files = 0

    # Display initial message
    print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}*{CYAN}]{RESET} {YELLOW}Initializing neural scan of {GREEN}'{scan_path}'{YELLOW}...{RESET}")

    # Setup color pack for animation function
    color_pack = (CYAN, BRIGHT_MAGENTA, YELLOW, RESET, BOLD)

    # Select a random funny message
    funny_msg = random.choice(FUNNY_MESSAGES)

    # Start counting files with animation
    file_count_thread_active = True

    def count_files_task():
        nonlocal total_files
        for root, dirs, files in os.walk(scan_path):
            total_files += len(files)
            if not file_count_thread_active:
                break

    # Use threading to count files while showing animation
    file_count_thread = threading.Thread(target=count_files_task)
    file_count_thread.start()

    # Show animation while counting
    animation_count = 0
    while file_count_thread.is_alive():
        knight_rider_animation(funny_msg, iterations=1, colors=color_pack)
        animation_count += 1
        # Change the message occasionally for variety
        if animation_count % 3 == 0:
            funny_msg = random.choice(FUNNY_MESSAGES)

    file_count_thread_active = False
    file_count_thread.join()

    # Gather file sizes with progress indication
    file_sizes = []
    file_count = 0

    # Progress bar configuration
    bar_width = 30
    last_update_time = 0
    update_interval = 0.1  # seconds between updates, to avoid flicker

    # Start the scan with cyberpunk styling
    print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}!{CYAN}]{RESET} {BRIGHT_CYAN}COMMENCING DEEP SCAN{RESET} of {YELLOW}{total_files}{RESET} files in {GREEN}'{scan_path}'{RESET}")
    print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}>{CYAN}]{RESET} {YELLOW}Stand by for data analysis...{RESET}")

    # For throttling progress updates
    import time

    # Create a variable to track the single progress line
    progress_line = ""

    # Initialize progress display with a completely different terminal approach
    # This disables normal line buffering by using a special escape sequence
    if use_progress:
        # Print a specific message that will be overwritten
        print(f"{CYAN}[{BRIGHT_MAGENTA}···{CYAN}] {YELLOW}Preparing scan environment...{RESET}")
        # Now move cursor back up one line so we can overwrite it
        sys.stdout.write("\033[1A\r")
        sys.stdout.flush()

    # Start tracking time for updates
    current_time = time.time()

    for root, dirs, files in os.walk(scan_path):
        rel_path = os.path.relpath(root, scan_path)
        rel_path = '.' if rel_path == '.' else f".../{rel_path}"

        for name in files:
            file_count += 1

            # Only update progress periodically to reduce terminal output
            current_time = time.time()
            should_update = (current_time - last_update_time) >= update_interval

            # Process the file
            full_path = os.path.join(root, name)
            try:
                size = os.path.getsize(full_path)
                file_sizes.append((full_path, size))
            except (OSError, PermissionError):
                continue

            # Update progress display if it's time
            if use_progress and (should_update or file_count == total_files):
                last_update_time = current_time

                # Calculate progress values
                percent = min(100, int(file_count / total_files * 100))
                filled_length = int(bar_width * file_count // total_files)
                bar = '█' * filled_length + '░' * (bar_width - filled_length)

                # Truncate path if needed
                max_path_len = term_width - 60
                if len(rel_path) > max_path_len:
                    show_path = "..." + rel_path[-max_path_len+3:]
                else:
                    show_path = rel_path

                # Create cyberpunk-style progress string
                scan_symbol = "▓▒░" if file_count % 3 == 0 else "░▒▓" if file_count % 3 == 1 else "▒▓░"
                progress_str = f"{CYAN}[{BRIGHT_MAGENTA}{scan_symbol}{CYAN}] {BRIGHT_CYAN}SCANNING{RESET}: {BAR_COLOR}[{bar}]{RESET} {YELLOW}{percent}%{RESET} | {MAGENTA}{file_count}/{total_files}{RESET} | {GREEN}{show_path}{RESET}"

                # Use a more forceful approach to control the cursor and line updating
                # This clears the ENTIRE current line and moves cursor to beginning
                sys.stdout.write("\033[2K\r")

                # Now write the progress string
                sys.stdout.write(progress_str)
                sys.stdout.flush()

                # Add small delay to ensure terminal updates properly
                time.sleep(0.05)

    # Display cyberpunk-style completion message, using the same forceful approach
    if use_progress:
        completion_msg = f"{CYAN}[{BRIGHT_MAGENTA}■■■{CYAN}] {BRIGHT_CYAN}SCAN COMPLETED{RESET}: {BAR_COLOR}[{bar_width*'█'}]{RESET} {YELLOW}100%{RESET} | {MAGENTA}{file_count}/{total_files}{RESET} files processed. {GREEN}Analysis ready.{RESET}"

        # Clear entire line and move to beginning
        sys.stdout.write("\033[2K\r")

        # Write completion message
        sys.stdout.write(completion_msg)

        # End with a newline for the next output
        sys.stdout.write("\n")
        sys.stdout.flush()

    if not file_sizes:
        print(f"No files found under '{scan_path}'.")
        return

    # Sort and select top N
    file_sizes.sort(key=lambda x: x[1], reverse=True)
    top_files = file_sizes[:args.top]
    max_size = top_files[0][1]

    # Render cyberpunk-style chart header with box drawing
    print(f"\n{BOLD}{ACCENT_COLOR}┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓{RESET}")
    print(f"{BOLD}{ACCENT_COLOR}┃ {HEADER_COLOR}TARGET ACQUIRED: {BRIGHT_CYAN}TOP {len(top_files)} SPACE HOGS IDENTIFIED{ACCENT_COLOR} ┃{RESET}")
    print(f"{BOLD}{ACCENT_COLOR}┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛{RESET}")

    # Table header with cyberpunk styling
    print(f"{BOLD}{ACCENT_COLOR}┌─{'─'*2}──{'─'*(args.width+2)}──{'─'*10}──{'─'*30}─┐{RESET}")
    print(f"{BOLD}{ACCENT_COLOR}│ {HEADER_COLOR}#{ACCENT_COLOR} │ {HEADER_COLOR}{'SIZE ALLOCATION':^{args.width}}{ACCENT_COLOR} │ {HEADER_COLOR}{'VOLUME':^10}{ACCENT_COLOR} │ {HEADER_COLOR}{'LOCATION PATH':^30}{ACCENT_COLOR} │{RESET}")
    print(f"{BOLD}{ACCENT_COLOR}├─{'─'*2}──{'─'*(args.width+2)}──{'─'*10}──{'─'*30}─┤{RESET}")

    # Render each file as a cyberpunk-style data entry
    for idx, (path, size) in enumerate(top_files, start=1):
        bar_len = int((size / max_size) * args.width) if max_size > 0 else 0

        # Use bright cyan for the progress bar with a glowing effect
        bar_full = BLOCK * bar_len
        bar_empty = '·' * (args.width - bar_len)  # Using dots instead of spaces for empty space
        bar = f"{BAR_COLOR}{bar_full}{ACCENT_COLOR}{bar_empty}"

        # Format size with bright magenta
        human = human_readable(size)
        size_str = f"{SIZE_COLOR}{human:>9}{RESET}"

        # Format path with green color
        path_display = path
        if len(path) > 40:
            path_display = "..." + path[-37:]

        # Print the row with cyberpunk styling
        print(f"{BOLD}{ACCENT_COLOR}│ {YELLOW}{idx:>2}{ACCENT_COLOR} │ {bar} │ {size_str} │ {PATH_COLOR}{path_display}{RESET}{' ' * (30 - len(path_display))}{ACCENT_COLOR} │{RESET}")

    # Close the table
    print(f"{BOLD}{ACCENT_COLOR}└─{'─'*2}──{'─'*(args.width+2)}──{'─'*10}──{'─'*30}─┘{RESET}")

    # Print total size info with cyberpunk styling
    total_size = sum(size for _, size in top_files)
    print(f"\n{ACCENT_COLOR}[{BRIGHT_CYAN}SYS{ACCENT_COLOR}] {HEADER_COLOR}Total data volume: {SIZE_COLOR}{human_readable(total_size)}{RESET}")
    print(f"{ACCENT_COLOR}[{BRIGHT_CYAN}SYS{ACCENT_COLOR}] {HEADER_COLOR}Target directory: {PATH_COLOR}{scan_path}{RESET}")
    print(f"{ACCENT_COLOR}[{BRIGHT_CYAN}SYS{ACCENT_COLOR}] {YELLOW}Scan complete. {GREEN}Have a nice day.{RESET}")

    # Properly shutdown security system
    try:
        if 'security_enabled' in locals() and security_enabled:
            audit_logger.log_shutdown({"clean_exit": True})
    except Exception:
        pass  # Don't let shutdown errors affect the main program


if __name__ == '__main__':
    main()
