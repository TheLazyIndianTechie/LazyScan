#!/usr/bin/env python3
"""
Configuration management for LazyScan.
Handles user preferences, disclaimer tracking, and application settings.
"""

import configparser
import os
from datetime import datetime

from ..core.logging_config import get_logger

logger = get_logger(__name__)

# Configuration paths
CONFIG_DIR = os.path.expanduser("~/.config/lazyscan")
CONFIG_FILE = os.path.join(CONFIG_DIR, "preferences.ini")


class LazyScanConfig:
    """Manages LazyScan configuration and user preferences."""

    def __init__(self, config_file: str = CONFIG_FILE):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.load_config()

    def load_config(self) -> None:
        """Load configuration from file."""
        try:
            if os.path.exists(self.config_file):
                self.config.read(self.config_file)
                logger.debug("Configuration loaded", config_file=self.config_file)
            else:
                logger.debug("No existing configuration file found")
        except Exception as e:
            logger.warning(
                "Failed to load configuration",
                config_file=self.config_file,
                error=str(e),
            )

    def save_config(self) -> None:
        """Save configuration to file."""
        try:
            # Create config directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)

            with open(self.config_file, "w") as f:
                self.config.write(f)

            logger.debug("Configuration saved", config_file=self.config_file)

        except Exception as e:
            logger.error(
                "Failed to save configuration",
                config_file=self.config_file,
                error=str(e),
            )
            raise

    def has_seen_disclaimer(self, version: str) -> bool:
        """Check if user has seen and acknowledged the disclaimer for this version."""
        try:
            return self.config.getboolean("disclaimer", "acknowledged", fallback=False)
        except Exception as e:
            logger.debug("Error checking disclaimer status", error=str(e))
            return False

    def mark_disclaimer_acknowledged(self, version: str) -> None:
        """Mark the disclaimer as acknowledged with timestamp and version."""
        try:
            if not self.config.has_section("disclaimer"):
                self.config.add_section("disclaimer")

            self.config.set("disclaimer", "acknowledged", "true")
            self.config.set(
                "disclaimer", "acknowledged_date", datetime.now().isoformat()
            )
            self.config.set("disclaimer", "version", version)

            self.save_config()

            logger.info(
                "Disclaimer acknowledged",
                version=version,
                timestamp=datetime.now().isoformat(),
            )

        except Exception as e:
            logger.error(
                "Failed to mark disclaimer as acknowledged",
                version=version,
                error=str(e),
            )
            raise

    def get_user_preference(self, section: str, key: str, default=None):
        """Get a user preference value."""
        try:
            if self.config.has_section(section) and self.config.has_option(
                section, key
            ):
                return self.config.get(section, key)
            return default
        except Exception as e:
            logger.debug(
                "Error getting user preference", section=section, key=key, error=str(e)
            )
            return default

    def set_user_preference(self, section: str, key: str, value: str) -> None:
        """Set a user preference value."""
        try:
            if not self.config.has_section(section):
                self.config.add_section(section)

            self.config.set(section, key, str(value))
            self.save_config()

            logger.debug("User preference set", section=section, key=key, value=value)

        except Exception as e:
            logger.error(
                "Failed to set user preference",
                section=section,
                key=key,
                value=value,
                error=str(e),
            )
            raise


# Global configuration instance
_config_instance = None


def get_config() -> LazyScanConfig:
    """Get the global configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = LazyScanConfig()
    return _config_instance


# Convenience functions for backward compatibility
def has_seen_disclaimer(version: str = "0.5.0") -> bool:
    """Check if user has seen and acknowledged the disclaimer."""
    return get_config().has_seen_disclaimer(version)


def mark_disclaimer_acknowledged(version: str = "0.5.0") -> None:
    """Mark the disclaimer as acknowledged."""
    return get_config().mark_disclaimer_acknowledged(version)
