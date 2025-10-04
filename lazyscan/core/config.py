#!/usr/bin/env python3
"""
Configuration management for LazyScan.
Handles user preferences, settings persistence, and defaults.
Supports TOML-based configuration file with migration from INI.
"""

from pathlib import Path
from typing import Any, Dict, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
import platformdirs
import configparser
import fcntl
import time

from ..core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class GeneralConfig:
    """General application settings."""
    bar_width: int = 40
    show_logo: bool = True
    use_colors: bool = True
    knight_rider_animation: bool = True
    theme: str = "default"
    unicode_art: bool = True


@dataclass
class ScanConfig:
    """Scanning configuration."""
    top_files: int = 20
    min_size_mb: int = 0
    exclude_patterns: List[str] = field(default_factory=lambda: [".git", "__pycache__", "node_modules"])
    follow_symlinks: bool = False
    max_depth: Optional[int] = None


@dataclass
class UnityConfig:
    """Unity-specific settings."""
    hub_projects_path: Optional[str] = None
    include_build_dirs: bool = False
    cache_cleanup_enabled: bool = True
    project_scan_depth: int = 3
    include_global_cache: bool = True
    version_aware_cache: bool = True


@dataclass
class SecurityConfig:
    """Security and safety settings."""
    enable_backups: bool = True
    backup_dir: str = ""
    confirm_deletions: bool = True
    safe_delete_enabled: bool = True
    max_concurrent_operations: int = 4

    # Cache management settings
    cache_retention_days: int = 30
    cache_cleanup_enabled: bool = True
    allow_admin_operations: bool = False
    docker_cleanup_enabled: bool = False
    system_cache_cleanup_enabled: bool = False


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "console"
    log_file: Optional[str] = None
    structured_logging: bool = True


@dataclass
class FirstRunConfig:
    """First run and user acknowledgment."""
    disclaimer_shown: bool = False
    first_launch: bool = True


@dataclass
class LazyScanConfig:
    """Complete LazyScan configuration with typed accessors."""
    general: GeneralConfig = field(default_factory=GeneralConfig)
    scan: ScanConfig = field(default_factory=ScanConfig)
    unity: UnityConfig = field(default_factory=UnityConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    first_run: FirstRunConfig = field(default_factory=FirstRunConfig)
    themes: Dict[str, Any] = field(default_factory=dict)
    apps: Dict[str, Any] = field(default_factory=dict)
    cache_targets: Dict[str, Any] = field(default_factory=dict)
    last_run: Optional[str] = None

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "LazyScanConfig":
        """Create a LazyScanConfig instance from a configuration dictionary."""
        # Set backup_dir with proper path resolution
        if "security" in config_dict and "backup_dir" in config_dict["security"]:
            config_dict["security"]["backup_dir"] = config_dict["security"]["backup_dir"]

        return cls(
            general=GeneralConfig(**config_dict.get("general", {})),
            scan=ScanConfig(**config_dict.get("scan", {})),
            unity=UnityConfig(**config_dict.get("unity", {})),
            security=SecurityConfig(**config_dict.get("security", {})),
            logging=LoggingConfig(**config_dict.get("logging", {})),
            first_run=FirstRunConfig(**config_dict.get("first_run", {})),
            themes=config_dict.get("themes", {}),
            apps=config_dict.get("apps", {}),
            cache_targets=config_dict.get("cache_targets", {}),
            last_run=config_dict.get("last_run"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert the configuration back to a dictionary."""
        return {
            "general": self.general.__dict__,
            "scan": self.scan.__dict__,
            "unity": self.unity.__dict__,
            "security": self.security.__dict__,
            "logging": self.logging.__dict__,
            "first_run": self.first_run.__dict__,
            "themes": self.themes,
            "apps": self.apps,
            "cache_targets": self.cache_targets,
            "last_run": self.last_run,
        }


# Try to import TOML libraries
TOML_READ_AVAILABLE = False
TOML_WRITE_AVAILABLE = False

try:
    import tomllib  # Python 3.11+
    TOML_READ_AVAILABLE = True
except ImportError:
    # For Python < 3.11, use tomli if available
    try:
        import tomli as tomllib  # type: ignore
        TOML_READ_AVAILABLE = True
    except ImportError:
        tomllib = None

try:
    import tomli_w  # type: ignore
    TOML_WRITE_AVAILABLE = True
except ImportError:
    tomli_w = None


class ConfigManager:
    """Manages LazyScan configuration with TOML-based storage and migration support."""

    def __init__(self):
        """Initialize the configuration manager."""
        self._config_dir = Path(platformdirs.user_config_dir("lazyscan"))
        self._config_file = self._config_dir / "config.toml"
        self._legacy_ini_file = self._config_dir / "preferences.ini"
        self._cache: Optional[Dict[str, Any]] = None
        self._ensure_config_dir()

    def _ensure_config_dir(self) -> None:
        """Ensure the configuration directory exists."""
        try:
            self._config_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not create config directory {self._config_dir}: {e}")

    @property
    def config_dir(self) -> Path:
        """Get the configuration directory path."""
        return self._config_dir

    @property
    def config_file(self) -> Path:
        """Get the configuration file path."""
        return self._config_file

    @property
    def legacy_ini_file(self) -> Path:
        """Get the legacy INI file path."""
        return self._legacy_ini_file

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from TOML file or return defaults."""
        if self._cache is not None:
            return self._cache

        config = DEFAULT_CONFIG.copy()

        # Check for migration from legacy INI
        if not self._config_file.exists() and self._legacy_ini_file.exists():
            logger.info("Legacy INI configuration detected, migrating to TOML")
            migrated_config = self._migrate_ini_to_toml()
            if migrated_config:
                config = migrated_config
                self._save_config(config)
                logger.info("Configuration migration completed")

        # Load TOML config if available
        if self._config_file.exists() and TOML_READ_AVAILABLE and tomllib:
            try:
                with open(self._config_file, "rb") as f:
                    loaded = tomllib.load(f)

                # Deep merge the loaded config with defaults
                def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
                    result = base.copy()
                    for key, value in override.items():
                        if (
                            key in result
                            and isinstance(result[key], dict)
                            and isinstance(value, dict)
                        ):
                            result[key] = deep_merge(result[key], value)
                        else:
                            result[key] = value
                    return result

                config = deep_merge(config, loaded)
                logger.debug("Configuration loaded from TOML file")

                # Apply per-application overrides if any app context is provided
                config = self._apply_app_overrides(config)
            except Exception as e:
                logger.warning(f"Failed to load config from {self._config_file}: {e}. Using defaults.")

        # Update last_run
        config["last_run"] = datetime.now().isoformat()
        self._cache = config
        return config

    def _apply_app_overrides(self, config: Dict[str, Any], app_name: Optional[str] = None) -> Dict[str, Any]:
        """Apply per-application overrides to the configuration.

        Args:
            config: The base configuration dictionary
            app_name: Optional application name to apply overrides for

        Returns:
            Configuration with overrides applied
        """
        if not app_name or "apps" not in config or app_name not in config["apps"]:
            return config

        result = config.copy()
        overrides = config["apps"][app_name]

        # Apply dotted key overrides
        for dotted_key, value in overrides.items():
            keys = dotted_key.split(".")
            target = result
            for key in keys[:-1]:
                if key not in target or not isinstance(target[key], dict):
                    target[key] = {}
                target = target[key]
            target[keys[-1]] = value

        logger.debug(f"Applied {len(overrides)} overrides for app '{app_name}'")
        return result

    def get_config_for_app(self, app_name: str) -> Dict[str, Any]:
        """Get configuration with overrides applied for a specific application."""
        config = self.load_config()
        return self._apply_app_overrides(config, app_name)

    def get_typed_config(self) -> LazyScanConfig:
        """Get the configuration as a typed LazyScanConfig object."""
        config_dict = self.load_config()
        return LazyScanConfig.from_dict(config_dict)

    def get_typed_config_for_app(self, app_name: str) -> LazyScanConfig:
        """Get typed configuration with overrides applied for a specific application."""
        config_dict = self.get_config_for_app(app_name)
        return LazyScanConfig.from_dict(config_dict)

    def _migrate_ini_to_toml(self) -> Optional[Dict[str, Any]]:
        """Migrate legacy INI configuration to TOML format."""
        if not self._legacy_ini_file.exists():
            return None

        try:
            parser = configparser.ConfigParser()
            parser.read(self._legacy_ini_file)

            migrated = DEFAULT_CONFIG.copy()

            # Migration mapping from old INI sections to new TOML sections
            section_mapping = {
                "ui": "general",  # ui section becomes general
                "scanning": "scan",  # scanning section becomes scan
                # security, logging, first_run sections remain the same
            }

            # Migrate known sections
            for old_section, new_section in section_mapping.items():
                if parser.has_section(old_section):
                    section_data = dict(parser.items(old_section))
                    migrated[new_section].update(self._convert_ini_values(section_data))

            # Handle sections that don't change names
            for section_name in ["security", "logging", "first_run"]:
                if parser.has_section(section_name):
                    section_data = dict(parser.items(section_name))
                    migrated[section_name].update(self._convert_ini_values(section_data))

            # Special handling for themes (if they existed in INI)
            if parser.has_section("themes"):
                # Themes in INI would be complex, for now just log
                logger.debug("Theme migration from INI not implemented yet")

            logger.info(f"Successfully migrated configuration from {self._legacy_ini_file}")
            return migrated

        except Exception as e:
            logger.error(f"Failed to migrate INI config: {e}")
            return None

    def _convert_ini_values(self, ini_dict: Dict[str, str]) -> Dict[str, Any]:
        """Convert INI string values to appropriate Python types."""
        converted = {}

        for key, value in ini_dict.items():
            # Try to convert common types
            if value.lower() in ("true", "1", "yes", "on"):
                converted[key] = True
            elif value.lower() in ("false", "0", "no", "off"):
                converted[key] = False
            elif value.isdigit():
                converted[key] = int(value)
            elif value.replace(".", "").isdigit() and value.count(".") == 1:
                try:
                    converted[key] = float(value)
                except ValueError:
                    converted[key] = value
            elif value.startswith("[") and value.endswith("]"):
                # Handle list values (basic parsing)
                try:
                    # Remove brackets and split by comma
                    list_content = value[1:-1].strip()
                    if list_content:
                        # Simple comma-separated list
                        items = [item.strip().strip('"').strip("'") for item in list_content.split(",")]
                        converted[key] = items
                    else:
                        converted[key] = []
                except Exception:
                    converted[key] = value
            else:
                converted[key] = value

        return converted

    def _save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to TOML file using atomic write operations."""
        if not TOML_WRITE_AVAILABLE or not tomli_w:
            logger.warning("TOML write support not available, cannot save config")
            return

        import tempfile
        import os

        lock_path = self._config_dir / ".config.lock"
        temp_path = None

        try:
            # Acquire file lock to prevent concurrent writes
            with open(lock_path, 'w') as lock_file:
                if os.name != 'nt':  # Unix-like systems
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                # On Windows, file locking is handled differently, but for simplicity
                # we'll rely on atomic rename operations

                # Ensure config directory exists
                self._config_dir.mkdir(parents=True, exist_ok=True)

                # Remove non-serializable fields for persistence
                persistent_config = config.copy()
                if "last_run" in persistent_config:
                    del persistent_config["last_run"]

                # Use atomic write with tempfile + replace
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    dir=self._config_dir,
                    prefix=".config-",
                    suffix=".toml",
                    delete=False
                ) as temp_file:
                    tomli_w.dump(persistent_config, temp_file)  # type: ignore
                    temp_path = temp_file.name

                # Atomic replace
                if os.name == 'nt':  # Windows
                    # On Windows, we need to remove the target file first
                    if self._config_file.exists():
                        self._config_file.unlink()
                    os.rename(temp_path, self._config_file)
                else:  # Unix-like systems
                    os.rename(temp_path, self._config_file)

                logger.debug(f"Configuration saved atomically to {self._config_file}")

        except Exception as e:
            logger.error(f"Failed to save config to {self._config_file}: {e}")
            # Clean up temp file if it still exists
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass  # Ignore cleanup errors
        finally:
            # Clean up lock file
            try:
                if lock_path.exists():
                    lock_path.unlink()
            except Exception:
                pass  # Ignore cleanup errors

    def save_config(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Save configuration to TOML file."""
        if config is None:
            config = self.load_config()
        self._save_config(config)

    def get_config(self) -> Dict[str, Any]:
        """Get the current configuration, loading if necessary."""
        return self.load_config()

    def update_config(self, key: str, value: Any, save: bool = True) -> None:
        """Update a configuration value and optionally save."""
        config = self.load_config()
        keys = key.split(".")
        d = config
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = value

        # Update cache
        self._cache = config

        if save:
            self.save_config(config)

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a config value by dotted key."""
        config = self.load_config()
        keys = key.split(".")
        value = config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def reset_config(self) -> None:
        """Reset configuration to defaults."""
        self._cache = None

        try:
            if self._config_file.exists():
                self._config_file.unlink()
            logger.info("Configuration reset to defaults")
        except Exception as e:
            logger.error(f"Failed to reset configuration: {e}")


# Global configuration manager instance
_config_manager = ConfigManager()

# TOML Configuration Schema Documentation
#
# The LazyScan configuration uses TOML format with the following structure:
#
# [general]
# bar_width = 40
# show_logo = true
# use_colors = true
# knight_rider_animation = true
# theme = "default"
# unicode_art = true
#
# [scan]
# top_files = 20
# min_size_mb = 0
# exclude_patterns = [".git", "__pycache__", "node_modules"]
# follow_symlinks = false
# max_depth = 10  # null for unlimited
#
# [unity]
# hub_projects_path = "/path/to/unity/projects"  # null for auto-detection
# include_build_dirs = false
# cache_cleanup_enabled = true
# project_scan_depth = 3
#
# [security]
# enable_backups = true
# backup_dir = "~/.config/lazyscan/backups"
# confirm_deletions = true
# safe_delete_enabled = true
# max_concurrent_operations = 4
#
# [logging]
# level = "INFO"
# format = "console"
# log_file = null
# structured_logging = true
#
# [first_run]
# disclaimer_shown = false
# first_launch = true
#
# [apps]
# # Per-application overrides (dotted keys override main config)
# [apps.unity]
# "scan.top_files" = 50
# "security.confirm_deletions" = false
#
# [apps.chrome]
# "scan.exclude_patterns" = [".git", "Cache", "Application Cache"]
#

# Default configuration
DEFAULT_CONFIG = {
    # General application settings
    "general": {
        "bar_width": 40,
        "show_logo": True,
        "use_colors": True,
        "knight_rider_animation": True,
        "theme": "default",
        "unicode_art": True,
    },
    # Scanning configuration
    "scan": {
        "top_files": 20,
        "min_size_mb": 0,
        "exclude_patterns": [".git", "__pycache__", "node_modules"],
        "follow_symlinks": False,
        "max_depth": None,
    },
    # Unity-specific settings
    "unity": {
        "hub_projects_path": None,  # Auto-detected
        "include_build_dirs": False,
        "cache_cleanup_enabled": True,
        "project_scan_depth": 3,
        "include_global_cache": True,
        "version_aware_cache": True,
    },
    # Security and safety settings
    "security": {
        "enable_backups": True,
        "backup_dir": str(_config_manager.config_dir / "backups"),
        "confirm_deletions": True,
        "safe_delete_enabled": True,
        "max_concurrent_operations": 4,
        # Cache management settings
        "cache_retention_days": 30,
        "cache_cleanup_enabled": True,
        "allow_admin_operations": False,
        "docker_cleanup_enabled": False,
        "system_cache_cleanup_enabled": False,
    },
    # Logging configuration
    "logging": {
        "level": "INFO",
        "format": "console",
        "log_file": None,
        "structured_logging": True,
    },
    # First run and user acknowledgment
    "first_run": {
        "disclaimer_shown": False,
        "first_launch": True,
    },
    # Theme definitions
    "themes": {
        "default": {
            "primary": "\033[36m",  # CYAN
            "accent": "\033[35m",   # MAGENTA
            "warning": "\033[33m",  # YELLOW
            "success": "\033[92m",  # GREEN
            "logo": [
                "╔══════════════════════════════════════════════╗",
                "║  LAZY SCAN - The Lazy Developer's Disk Tool  ║",
                "║           Find what's eating your space      ║",
                "╚══════════════════════════════════════════════╝",
            ],
            "glyphs": {
                "scanner": "▮▯▯",
                "progress_filled": "█",
                "progress_empty": "░",
                "progress_medium": "▓",
                "progress_light": "▒",
                "file_python": "🐍",
                "file_text": "📄",
                "file_archive": "📦",
                "file_generic": "📄",
                "file_directory": "📁",
            },
            "animations": {
                "knight_rider_delay": 0.07,
                "progress_update_interval": 0.1,
            }
        },
        "minimal": {
            "primary": "\033[37m",  # WHITE
            "accent": "\033[90m",   # GRAY
            "warning": "\033[33m",  # YELLOW
            "success": "\033[92m",  # GREEN
            "logo": [
                "+----------------------------------------------+",
                "|  LAZY SCAN - The Lazy Developer's Disk Tool  |",
                "|           Find what's eating your space      |",
                "+----------------------------------------------+",
            ],
            "glyphs": {
                "scanner": "[=]",
                "progress_filled": "#",
                "progress_empty": "-",
                "progress_medium": "=",
                "progress_light": "~",
                "file_python": "[PY]",
                "file_text": "[TXT]",
                "file_archive": "[ARC]",
                "file_generic": "[FIL]",
                "file_directory": "[DIR]",
            },
            "animations": {
                "knight_rider_delay": 0.1,
                "progress_update_interval": 0.15,
            }
        }
    },
    # Per-application overrides
    "apps": {
        # Example structure for per-app overrides
        # "unity": {
        #     "scan.top_files": 50,
        #     "security.confirm_deletions": False,
        # },
        # "chrome": {
        #     "scan.exclude_patterns": [".git", "Cache", "Application Cache"],
        # },
    },
    # Cache target configurations
    "cache_targets": {
        # Platform-specific cache target configurations
        # "macos": {
        #     "homebrew": {"enabled": True, "retention_days": 30, "requires_admin": False, "safety_level": "safe"},
        #     "npm": {"enabled": True, "retention_days": 90, "requires_admin": False, "safety_level": "safe"},
        #     "pip": {"enabled": True, "retention_days": 90, "requires_admin": False, "safety_level": "safe"},
        #     "docker": {"enabled": False, "retention_days": None, "requires_admin": False, "safety_level": "dangerous"},
        # },
        # "linux": {
        #     "apt": {"enabled": True, "retention_days": 7, "requires_admin": True, "safety_level": "safe"},
        #     "yum": {"enabled": True, "retention_days": 7, "requires_admin": True, "safety_level": "safe"},
        #     "pacman": {"enabled": True, "retention_days": 30, "requires_admin": True, "safety_level": "safe"},
        #     "tmp": {"enabled": True, "retention_days": 7, "requires_admin": False, "safety_level": "caution"},
        # },
        # "windows": {
        #     "temp": {"enabled": True, "retention_days": 7, "requires_admin": False, "safety_level": "safe"},
        #     "prefetch": {"enabled": True, "retention_days": 30, "requires_admin": True, "safety_level": "safe"},
        #     "windows_update": {"enabled": False, "retention_days": None, "requires_admin": True, "safety_level": "dangerous"},
        #     "thumbnail": {"enabled": True, "retention_days": 30, "requires_admin": False, "safety_level": "safe"},
        # },
    },
    "last_run": None,
}


# Backward compatibility functions
def load_config() -> Dict[str, Any]:
    """Load configuration from TOML file or return defaults."""
    return _config_manager.load_config()


def save_config(config: Optional[Dict[str, Any]] = None) -> None:
    """Save configuration to TOML file."""
    _config_manager.save_config(config)


def get_config() -> Dict[str, Any]:
    """Get the current configuration, loading if necessary."""
    return _config_manager.get_config()


def update_config(key: str, value: Any, save: bool = True) -> None:
    """Update a configuration value and optionally save."""
    _config_manager.update_config(key, value, save)


def get_setting(key: str, default: Any = None) -> Any:
    """Get a config value by dotted key."""
    return _config_manager.get_setting(key, default)


def has_seen_disclaimer() -> bool:
    """Check if user has seen the disclaimer."""
    return get_setting("first_run.disclaimer_shown", False)


def mark_disclaimer_acknowledged() -> None:
    """Mark that the user has acknowledged the disclaimer."""
    update_config("first_run.disclaimer_shown", True, save=True)
    update_config("first_run.first_launch", False, save=True)


def is_first_run() -> bool:
    """Check if this is the first run of the application."""
    return get_setting("first_run.first_launch", True)


def get_ui_setting(key: str, default: Any = None) -> Any:
    """Get a UI-related setting."""
    return get_setting(f"ui.{key}", default)


def get_scanning_setting(key: str, default: Any = None) -> Any:
    """Get a scanning-related setting."""
    return get_setting(f"scanning.{key}", default)


def get_security_setting(key: str, default: Any = None) -> Any:
    """Get a security-related setting."""
    return get_setting(f"security.{key}", default)


def reset_config() -> None:
    """Reset configuration to defaults."""
    _config_manager.reset_config()


def get_typed_config() -> LazyScanConfig:
    """Get the configuration as a typed LazyScanConfig object."""
    return _config_manager.get_typed_config()


def get_config_info() -> Dict[str, Any]:
    """Get information about the configuration system."""
    return {
        "config_dir": str(_config_manager.config_dir),
        "config_file": str(_config_manager.config_file),
        "legacy_ini_file": str(_config_manager.legacy_ini_file),
        "config_exists": _config_manager.config_file.exists(),
        "legacy_ini_exists": _config_manager.legacy_ini_file.exists(),
        "toml_read_support": TOML_READ_AVAILABLE,
        "toml_write_support": TOML_WRITE_AVAILABLE,
        "first_run": is_first_run(),
        "disclaimer_shown": has_seen_disclaimer(),
    }