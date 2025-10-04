#!/usr/bin/env python3
"""
Linux platform-specific paths and configurations.
"""

from pathlib import Path
from platformdirs import user_cache_dir, user_data_dir
from typing import List

from ..core.cache_targets import CacheTarget, SafetyLevel

# Linux-specific cache paths
LINUX_CACHE_PATHS = [
    # System caches
    f"{user_cache_dir()}/",  # ~/.cache
    f"{user_data_dir()}/.local/share/Trash/",  # Trash
    f"{user_cache_dir()}/apt/archives/",  # Package manager cache (Ubuntu/Debian)
]

PERPLEXITY_PATHS = [
    f"{user_cache_dir()}/perplexity",
    f"{user_data_dir()}/.config/perplexity/cache/",
]

DIA_PATHS = [
    f"{user_data_dir()}/.local/share/dia/",
    f"{user_cache_dir()}/dia",
]

SLACK_PATHS = [
    f"{user_data_dir()}/.config/Slack/Cache/",
    f"{user_cache_dir()}/Slack",
]

DISCORD_PATHS = [
    f"{user_data_dir()}/.config/discord/Cache/",
    f"{user_data_dir()}/.config/discord/Code Cache/",
]

SPOTIFY_PATHS = [
    f"{user_data_dir()}/.cache/spotify/PersistentCache/",
    f"{user_cache_dir()}/spotify",
]

VSCODE_PATHS = [
    f"{user_data_dir()}/.config/Code/Cache/",
    f"{user_data_dir()}/.config/Code/logs/",
    f"{user_cache_dir()}/code",
]

ZOOM_PATHS = [
    f"{user_data_dir()}/.zoom/cache/",
    f"{user_data_dir()}/.local/share/zoom/",
]

TEAMS_PATHS = [
    f"{user_data_dir()}/.config/teams/Cache/",
    f"{user_data_dir()}/.config/teams/GPUCache/",
]

FIREFOX_PATHS = [
    f"{user_data_dir()}/.cache/mozilla/firefox/*/cache2/",
    f"{user_cache_dir()}/mozilla/firefox/",
]

SAFARI_PATHS: list[str] = []  # Safari is macOS-only, no Linux equivalent


def get_linux_cache_targets(config: dict = None) -> List[CacheTarget]:
    """
    Get Linux-specific cache targets with configuration-driven policies.

    Args:
        config: Optional configuration dictionary for cache targets

    Returns:
        List of CacheTarget instances for Linux
    """
    if config is None:
        config = {}

    # Get platform-specific config or use defaults
    linux_config = config.get("linux", {})

    cache_targets = []

    # User cache directory (~/.cache/*)
    user_cache_config = linux_config.get("user_cache", {"enabled": True, "retention_days": 30, "requires_admin": False, "safety_level": "caution"})
    if user_cache_config.get("enabled", True):
        cache_targets.append(CacheTarget(
            path=Path(user_cache_dir()),
            category="user_cache",
            requires_admin=user_cache_config.get("requires_admin", False),
            retention_days=user_cache_config.get("retention_days", 30),
            safety_level=SafetyLevel(user_cache_config.get("safety_level", "caution")),
            description="User cache directory containing various application caches"
        ))

    # APT archives (/var/cache/apt/archives/)
    apt_config = linux_config.get("apt", {"enabled": True, "retention_days": 7, "requires_admin": True, "safety_level": "safe"})
    if apt_config.get("enabled", True):
        apt_path = Path("/var/cache/apt/archives")
        if apt_path.exists():
            cache_targets.append(CacheTarget(
                path=apt_path,
                category="package_manager",
                requires_admin=apt_config.get("requires_admin", True),
                retention_days=apt_config.get("retention_days", 7),
                safety_level=SafetyLevel(apt_config.get("safety_level", "safe")),
                description="APT package manager downloaded archives (re-downloadable)"
            ))

    # YUM/DNF cache (/var/cache/yum/ or /var/cache/dnf/)
    yum_config = linux_config.get("yum", {"enabled": True, "retention_days": 7, "requires_admin": True, "safety_level": "safe"})
    if yum_config.get("enabled", True):
        # Check for both yum and dnf cache locations
        yum_paths = [Path("/var/cache/yum"), Path("/var/cache/dnf")]
        for yum_path in yum_paths:
            if yum_path.exists():
                cache_targets.append(CacheTarget(
                    path=yum_path,
                    category="package_manager",
                    requires_admin=yum_config.get("requires_admin", True),
                    retention_days=yum_config.get("retention_days", 7),
                    safety_level=SafetyLevel(yum_config.get("safety_level", "safe")),
                    description="YUM/DNF package manager cache (re-downloadable)"
                ))
                break  # Only add one of them

    # Pacman cache (/var/cache/pacman/pkg/)
    pacman_config = linux_config.get("pacman", {"enabled": True, "retention_days": 30, "requires_admin": True, "safety_level": "safe"})
    if pacman_config.get("enabled", True):
        pacman_path = Path("/var/cache/pacman/pkg")
        if pacman_path.exists():
            cache_targets.append(CacheTarget(
                path=pacman_path,
                category="package_manager",
                requires_admin=pacman_config.get("requires_admin", True),
                retention_days=pacman_config.get("retention_days", 30),
                safety_level=SafetyLevel(pacman_config.get("safety_level", "safe")),
                description="Pacman package manager cache (re-downloadable)"
            ))

    # SystemD journal (/var/log/journal/) - dangerous
    journal_config = linux_config.get("journal", {"enabled": False, "retention_days": None, "requires_admin": True, "safety_level": "dangerous"})
    if journal_config.get("enabled", False):
        journal_path = Path("/var/log/journal")
        if journal_path.exists():
            cache_targets.append(CacheTarget(
                path=journal_path,
                category="system_logs",
                requires_admin=journal_config.get("requires_admin", True),
                retention_days=journal_config.get("retention_days", None),
                safety_level=SafetyLevel(journal_config.get("safety_level", "dangerous")),
                description="SystemD journal logs (HIGH RISK - affects system monitoring)"
            ))

    # Temporary files (/tmp/)
    tmp_config = linux_config.get("tmp", {"enabled": True, "retention_days": 7, "requires_admin": False, "safety_level": "caution"})
    if tmp_config.get("enabled", True):
        cache_targets.append(CacheTarget(
            path=Path("/tmp"),
            category="temporary_files",
            requires_admin=tmp_config.get("requires_admin", False),
            retention_days=tmp_config.get("retention_days", 7),
            safety_level=SafetyLevel(tmp_config.get("safety_level", "caution")),
            description="System temporary files directory (aging-based cleanup)"
        ))

    # Docker (if available)
    docker_config = linux_config.get("docker", {"enabled": False, "retention_days": None, "requires_admin": False, "safety_level": "dangerous"})
    if docker_config.get("enabled", False):
        # Docker data root (usually /var/lib/docker)
        docker_path = Path("/var/lib/docker")
        if docker_path.exists():
            cache_targets.append(CacheTarget(
                path=docker_path,
                category="container",
                requires_admin=docker_config.get("requires_admin", False),
                retention_days=docker_config.get("retention_days", None),
                safety_level=SafetyLevel(docker_config.get("safety_level", "dangerous")),
                description="Docker container data and volumes (HIGH RISK - contains application data)"
            ))

    return cache_targets
