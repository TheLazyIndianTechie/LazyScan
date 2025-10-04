#!/usr/bin/env python3
"""
macOS platform-specific paths and configurations.
"""

from pathlib import Path
from platformdirs import user_cache_dir, user_data_dir
from typing import List

from ..core.cache_targets import CacheTarget, SafetyLevel

# Application cache paths for macOS
MACOS_CACHE_PATHS = [
    # System caches
    f"{user_cache_dir()}/",
    f"{user_data_dir()}/CrashReporter/",
    f"{user_data_dir()}/../Logs/",
    # Browser caches
    f"{user_cache_dir()}/Google/Chrome/",
    f"{user_cache_dir()}/com.apple.Safari/",
    # Common application caches
    f"{user_cache_dir()}/com.apple.dt.Xcode/",
    f"{user_cache_dir()}/com.microsoft.VSCode/",
    f"{user_cache_dir()}/Slack/",
    f"{user_cache_dir()}/Spotify/",
]

# Other application paths for macOS
PERPLEXITY_PATHS = [
    f"{user_cache_dir()}/Perplexity",
    f"{user_data_dir()}/Perplexity/Cache/",
    f"{user_data_dir()}/Perplexity/Code Cache/",
]

DIA_PATHS = [
    f"{user_data_dir()}/Dia/",
    f"{user_cache_dir()}/Dia",
]

SLACK_PATHS = [
    f"{user_data_dir()}/Slack/Cache/",
    f"{user_cache_dir()}/com.tinyspeck.slackmacgap",
]

DISCORD_PATHS = [
    f"{user_data_dir()}/discord/Cache/",
    f"{user_data_dir()}/discord/Code Cache/",
]

SPOTIFY_PATHS = [
    f"{user_data_dir()}/Spotify/PersistentCache/",
    f"{user_cache_dir()}/com.spotify.client",
]

VSCODE_PATHS = [
    f"{user_data_dir()}/Code/Cache/",
    f"{user_data_dir()}/Code/logs/",
]

ZOOM_PATHS = [
    f"{user_data_dir()}/zoom.us/Cache/",
    f"{user_data_dir()}/../Documents/Zoom/",
]

TEAMS_PATHS = [
    f"{user_data_dir()}/Microsoft/Teams/Cache/",
    f"{user_data_dir()}/Microsoft/Teams/GPUCache/",
]

FIREFOX_PATHS = [
    f"{user_data_dir()}/Firefox/Profiles/*/cache2/",
    f"{user_cache_dir()}/Firefox/",
]

SAFARI_PATHS = [
    f"{user_cache_dir()}/com.apple.Safari/",
    f"{user_data_dir()}/../Safari/Databases/",
]


def get_macos_cache_targets(config: dict = None) -> List[CacheTarget]:
    """
    Get macOS-specific cache targets with configuration-driven policies.

    Args:
        config: Optional configuration dictionary for cache targets

    Returns:
        List of CacheTarget instances for macOS
    """
    if config is None:
        config = {}

    # Get platform-specific config or use defaults
    macos_config = config.get("macos", {})

    cache_targets = []

    # Homebrew cache
    homebrew_config = macos_config.get("homebrew", {"enabled": True, "retention_days": 30, "requires_admin": False, "safety_level": "safe"})
    if homebrew_config.get("enabled", True):
        cache_targets.append(CacheTarget(
            path=Path(user_cache_dir()) / "Homebrew",
            category="package_manager",
            requires_admin=homebrew_config.get("requires_admin", False),
            retention_days=homebrew_config.get("retention_days", 30),
            safety_level=SafetyLevel(homebrew_config.get("safety_level", "safe")),
            description="Homebrew package manager cache and temporary files"
        ))

    # npm cache
    npm_config = macos_config.get("npm", {"enabled": True, "retention_days": 90, "requires_admin": False, "safety_level": "safe"})
    if npm_config.get("enabled", True):
        cache_targets.append(CacheTarget(
            path=Path.home() / ".npm",
            category="package_manager",
            requires_admin=npm_config.get("requires_admin", False),
            retention_days=npm_config.get("retention_days", 90),
            safety_level=SafetyLevel(npm_config.get("safety_level", "safe")),
            description="Node.js package manager cache"
        ))

    # pip cache
    pip_config = macos_config.get("pip", {"enabled": True, "retention_days": 90, "requires_admin": False, "safety_level": "safe"})
    if pip_config.get("enabled", True):
        cache_targets.append(CacheTarget(
            path=Path(user_cache_dir()) / "pip",
            category="package_manager",
            requires_admin=pip_config.get("requires_admin", False),
            retention_days=pip_config.get("retention_days", 90),
            safety_level=SafetyLevel(pip_config.get("safety_level", "safe")),
            description="Python package manager cache"
        ))

    # Docker (dangerous - disabled by default)
    docker_config = macos_config.get("docker", {"enabled": False, "retention_days": None, "requires_admin": False, "safety_level": "dangerous"})
    if docker_config.get("enabled", False):
        # Docker Desktop for Mac stores data in ~/Library/Containers/com.docker.docker
        docker_path = Path(user_data_dir()) / "../Containers/com.docker.docker/Data"
        if docker_path.exists():
            cache_targets.append(CacheTarget(
                path=docker_path,
                category="container",
                requires_admin=docker_config.get("requires_admin", False),
                retention_days=docker_config.get("retention_days", None),
                safety_level=SafetyLevel(docker_config.get("safety_level", "dangerous")),
                description="Docker Desktop container data and volumes (HIGH RISK - contains application data)"
            ))

    return cache_targets
