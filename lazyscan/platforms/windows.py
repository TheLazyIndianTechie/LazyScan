#!/usr/bin/env python3
"""
Windows platform-specific paths and configurations.
"""

from pathlib import Path
from platformdirs import user_cache_dir, user_data_dir
from typing import List
import os

from ..core.cache_targets import CacheTarget, SafetyLevel

# Windows-specific cache paths
WINDOWS_CACHE_PATHS = [
    f"{user_cache_dir()}/",
    f"{user_cache_dir()}/Temp/",
    f"{user_data_dir()}/Microsoft/Windows/INetCache/",
    f"{user_data_dir()}/Microsoft/Windows/Cookies/",
]

PERPLEXITY_PATHS = [
    f"{user_cache_dir()}/Perplexity/",
    f"{user_data_dir()}/Perplexity/Cache/",
]

DIA_PATHS = [
    f"{user_data_dir()}/Dia/",
    f"{user_cache_dir()}/Dia/",
]

SLACK_PATHS = [
    f"{user_data_dir()}/Slack/Cache/",
    f"{user_cache_dir()}/Slack/",
]

DISCORD_PATHS = [
    f"{user_cache_dir()}/discord/Cache/",
    f"{user_cache_dir()}/discord/Code Cache/",
    f"{user_data_dir()}/discord/Local Storage/",
]

SPOTIFY_PATHS = [
    f"{user_data_dir()}/Spotify/PersistentCache/",
    f"{user_cache_dir()}/Spotify/",
]

VSCODE_PATHS = [
    f"{user_data_dir()}/Code/Cache/",
    f"{user_data_dir()}/Code/Logs/",
    f"{user_cache_dir()}/Code/",
]

ZOOM_PATHS = [
    f"{user_cache_dir()}/zoom.us/Cache/",
    f"{user_data_dir()}/Zoom/",
]

TEAMS_PATHS = [
    f"{user_cache_dir()}/Microsoft/Teams/Cache/",
    f"{user_cache_dir()}/Microsoft/Teams/GPUCache/",
    f"{user_cache_dir()}/Microsoft/Teams/IndexingFiles/",
]

FIREFOX_PATHS = [
    f"{user_data_dir()}/Mozilla/Firefox/Profiles/*/cache2/",
    f"{user_cache_dir()}/Mozilla/Firefox/",
]

SAFARI_PATHS: list[str] = []  # Safari not available on Windows


def get_windows_cache_targets(config: dict = None) -> List[CacheTarget]:
    """
    Get Windows-specific cache targets with configuration-driven policies.

    Args:
        config: Optional configuration dictionary for cache targets

    Returns:
        List of CacheTarget instances for Windows
    """
    if config is None:
        config = {}

    # Get platform-specific config or use defaults
    windows_config = config.get("windows", {})

    cache_targets = []

    # Windows Temp directories (%TEMP%, %TMP%)
    temp_config = windows_config.get("temp", {"enabled": True, "retention_days": 7, "requires_admin": False, "safety_level": "safe"})
    if temp_config.get("enabled", True):
        # Add both %TEMP% and %TMP% if they exist and are different
        temp_paths = []
        temp_env = os.environ.get("TEMP")
        tmp_env = os.environ.get("TMP")

        if temp_env:
            temp_paths.append(Path(temp_env))
        if tmp_env and tmp_env != temp_env:
            temp_paths.append(Path(tmp_env))

        for temp_path in temp_paths:
            if temp_path.exists():
                cache_targets.append(CacheTarget(
                    path=temp_path,
                    category="temporary_files",
                    requires_admin=temp_config.get("requires_admin", False),
                    retention_days=temp_config.get("retention_days", 7),
                    safety_level=SafetyLevel(temp_config.get("safety_level", "safe")),
                    description="Windows temporary files directory"
                ))

    # Windows Update cache (%WINDIR%\SoftwareDistribution\Download\)
    windows_update_config = windows_config.get("windows_update", {"enabled": False, "retention_days": None, "requires_admin": True, "safety_level": "dangerous"})
    if windows_update_config.get("enabled", False):
        windir = os.environ.get("WINDIR", "C:\\Windows")
        update_path = Path(windir) / "SoftwareDistribution" / "Download"
        if update_path.exists():
            cache_targets.append(CacheTarget(
                path=update_path,
                category="system_updates",
                requires_admin=windows_update_config.get("requires_admin", True),
                retention_days=windows_update_config.get("retention_days", None),
                safety_level=SafetyLevel(windows_update_config.get("safety_level", "dangerous")),
                description="Windows Update downloaded files (HIGH RISK - affects system updates)"
            ))

    # Prefetch files (%WINDIR%\Prefetch\)
    prefetch_config = windows_config.get("prefetch", {"enabled": True, "retention_days": 30, "requires_admin": True, "safety_level": "safe"})
    if prefetch_config.get("enabled", True):
        windir = os.environ.get("WINDIR", "C:\\Windows")
        prefetch_path = Path(windir) / "Prefetch"
        if prefetch_path.exists():
            cache_targets.append(CacheTarget(
                path=prefetch_path,
                category="system_performance",
                requires_admin=prefetch_config.get("requires_admin", True),
                retention_days=prefetch_config.get("retention_days", 30),
                safety_level=SafetyLevel(prefetch_config.get("safety_level", "safe")),
                description="Windows Prefetch files for application startup optimization"
            ))

    # Thumbnail cache (%LOCALAPPDATA%\Microsoft\Windows\Explorer\)
    thumbnail_config = windows_config.get("thumbnail", {"enabled": True, "retention_days": 30, "requires_admin": False, "safety_level": "safe"})
    if thumbnail_config.get("enabled", True):
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            thumb_path = Path(local_appdata) / "Microsoft" / "Windows" / "Explorer"
            if thumb_path.exists():
                cache_targets.append(CacheTarget(
                    path=thumb_path,
                    category="thumbnails",
                    requires_admin=thumbnail_config.get("requires_admin", False),
                    retention_days=thumbnail_config.get("retention_days", 30),
                    safety_level=SafetyLevel(thumbnail_config.get("safety_level", "safe")),
                    description="Windows Explorer thumbnail cache (regenerates automatically)"
                ))

    # Windows Installer cache (%WINDIR%\Installer\)
    installer_config = windows_config.get("installer", {"enabled": False, "retention_days": None, "requires_admin": True, "safety_level": "dangerous"})
    if installer_config.get("enabled", False):
        windir = os.environ.get("WINDIR", "C:\\Windows")
        installer_path = Path(windir) / "Installer"
        if installer_path.exists():
            cache_targets.append(CacheTarget(
                path=installer_path,
                category="installer_cache",
                requires_admin=installer_config.get("requires_admin", True),
                retention_days=installer_config.get("retention_days", None),
                safety_level=SafetyLevel(installer_config.get("safety_level", "dangerous")),
                description="Windows Installer cached MSI files (HIGH RISK - affects uninstallation)"
            ))

    return cache_targets
