#!/usr/bin/env python3
"""
Cache target definitions and management for LazyScan.
Provides structured cache target definitions with retention policies,
safety classifications, and platform-specific configurations.
"""

from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class SafetyLevel(Enum):
    """Safety classification for cache operations."""
    SAFE = "safe"        # No data loss risk (caches, temp files)
    CAUTION = "caution"  # Potential performance impact (logs, thumbnails)
    DANGEROUS = "dangerous"  # Data loss risk (databases, system files)


@dataclass
class CacheTarget:
    """Represents a cache target with policy-driven management."""
    path: Path
    category: str
    requires_admin: bool = False
    retention_days: Optional[int] = None
    safety_level: SafetyLevel = SafetyLevel.SAFE
    description: str = ""
    enabled: bool = True

    def __post_init__(self):
        """Validate and normalize the cache target."""
        if isinstance(self.safety_level, str):
            self.safety_level = SafetyLevel(self.safety_level)
        if isinstance(self.path, str):
            self.path = Path(self.path)

    @property
    def is_expired(self) -> bool:
        """Check if this cache target has retention-based expiration."""
        if self.retention_days is None:
            return False

        if not self.path.exists():
            return False

        # For directories, check modification time of contents
        # For files, check modification time directly
        if self.path.is_file():
            mtime = self.path.stat().st_mtime
        elif self.path.is_dir():
            # Check if directory has any files older than retention period
            try:
                files = list(self.path.rglob("*"))
                if not files:
                    return False
                mtime = max(f.stat().st_mtime for f in files if f.is_file())
            except (OSError, PermissionError):
                return False
        else:
            return False

        import time
        age_days = (time.time() - mtime) / (24 * 3600)
        return age_days > self.retention_days

    def get_size_mb(self) -> float:
        """Calculate the size of this cache target in MB."""
        try:
            if self.path.is_file():
                return self.path.stat().st_size / (1024 * 1024)
            elif self.path.is_dir():
                total_size = 0
                for file_path in self.path.rglob("*"):
                    if file_path.is_file():
                        try:
                            total_size += file_path.stat().st_size
                        except (OSError, PermissionError):
                            continue
                return total_size / (1024 * 1024)
            else:
                return 0.0
        except (OSError, PermissionError):
            return 0.0


@dataclass
class CacheTargetConfig:
    """Configuration for a cache target."""
    enabled: bool = True
    retention_days: Optional[int] = None
    requires_admin: bool = False
    safety_level: str = "safe"

    def to_cache_target(self, path: Path, category: str, description: str = "") -> CacheTarget:
        """Convert this config to a CacheTarget instance."""
        return CacheTarget(
            path=path,
            category=category,
            requires_admin=self.requires_admin,
            retention_days=self.retention_days,
            safety_level=SafetyLevel(self.safety_level),
            description=description,
            enabled=self.enabled
        )


@dataclass
class PlatformCacheConfig:
    """Platform-specific cache configuration."""
    # macOS targets
    homebrew: CacheTargetConfig = field(default_factory=lambda: CacheTargetConfig(retention_days=30))
    npm: CacheTargetConfig = field(default_factory=lambda: CacheTargetConfig(retention_days=90))
    pip: CacheTargetConfig = field(default_factory=lambda: CacheTargetConfig(retention_days=90))
    docker: CacheTargetConfig = field(default_factory=lambda: CacheTargetConfig(enabled=False, safety_level="dangerous"))

    # Linux targets
    apt: CacheTargetConfig = field(default_factory=lambda: CacheTargetConfig(retention_days=7, requires_admin=True))
    yum: CacheTargetConfig = field(default_factory=lambda: CacheTargetConfig(retention_days=7, requires_admin=True))
    pacman: CacheTargetConfig = field(default_factory=lambda: CacheTargetConfig(retention_days=30, requires_admin=True))
    tmp: CacheTargetConfig = field(default_factory=lambda: CacheTargetConfig(retention_days=7, safety_level="caution"))

    # Windows targets
    temp: CacheTargetConfig = field(default_factory=lambda: CacheTargetConfig(retention_days=7))
    prefetch: CacheTargetConfig = field(default_factory=lambda: CacheTargetConfig(retention_days=30, requires_admin=True))
    windows_update: CacheTargetConfig = field(default_factory=lambda: CacheTargetConfig(enabled=False, safety_level="dangerous"))
    thumbnail: CacheTargetConfig = field(default_factory=lambda: CacheTargetConfig(retention_days=30))

    def get_config_for_target(self, target_name: str) -> Optional[CacheTargetConfig]:
        """Get configuration for a specific target."""
        return getattr(self, target_name, None)

    def set_config_for_target(self, target_name: str, config: CacheTargetConfig) -> None:
        """Set configuration for a specific target."""
        if hasattr(self, target_name):
            setattr(self, target_name, config)


@dataclass
class CacheManagementConfig:
    """Configuration for cache management features."""
    cache_retention_days: int = 30
    cache_cleanup_enabled: bool = True
    allow_admin_operations: bool = False
    docker_cleanup_enabled: bool = False
    system_cache_cleanup_enabled: bool = False

    # Platform-specific configurations
    platforms: Dict[str, PlatformCacheConfig] = field(default_factory=lambda: {
        "macos": PlatformCacheConfig(),
        "linux": PlatformCacheConfig(),
        "windows": PlatformCacheConfig()
    })

    def get_platform_config(self, platform: str) -> PlatformCacheConfig:
        """Get cache configuration for a specific platform."""
        return self.platforms.get(platform, PlatformCacheConfig())

    def set_platform_config(self, platform: str, config: PlatformCacheConfig) -> None:
        """Set cache configuration for a specific platform."""
        self.platforms[platform] = config