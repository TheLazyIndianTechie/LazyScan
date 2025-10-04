#!/usr/bin/env python3
"""
Audit Encryption Schema Validation and Configuration

This module provides validation and handling for the expanded security.audit
encryption schema with backward compatibility support.
"""

import os
import sys
import json
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

from ..core.errors import SecurityPolicyError


class EncryptionAlgorithm(Enum):
    """Supported encryption algorithms."""
    AES_256_GCM = "AES-256-GCM"


class KeyProvider(Enum):
    """Supported key storage providers."""
    AUTO = "auto"
    KEYCHAIN = "keychain"  # macOS
    CREDENTIAL_MANAGER = "credential-manager"  # Windows
    SECRET_SERVICE = "secret-service"  # Linux
    CUSTOM = "custom"


class MigrationMode(Enum):
    """Migration modes for encryption rollout."""
    AUTO = "auto"
    MANUAL = "manual"
    DISABLED = "disabled"


@dataclass
class AuditEncryptionConfig:
    """Configuration for audit log encryption."""

    enabled: bool = True
    algorithm: str = EncryptionAlgorithm.AES_256_GCM.value
    key_provider: str = KeyProvider.AUTO.value
    key_rotation_days: int = 90
    migration_mode: str = MigrationMode.AUTO.value
    tamper_detection: bool = True
    recovery_decryption: bool = True

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate()

    def _validate(self):
        """Validate the encryption configuration."""
        # Validate algorithm
        if self.algorithm not in [e.value for e in EncryptionAlgorithm]:
            raise SecurityPolicyError(
                f"Unsupported encryption algorithm: {self.algorithm}. "
                f"Supported: {[e.value for e in EncryptionAlgorithm]}"
            )

        # Validate key provider
        if self.key_provider not in [e.value for e in KeyProvider]:
            raise SecurityPolicyError(
                f"Unsupported key provider: {self.key_provider}. "
                f"Supported: {[e.value for e in KeyProvider]}"
            )

        # Validate key rotation days
        if self.key_rotation_days < 0:
            raise SecurityPolicyError(
                f"key_rotation_days must be non-negative, got: {self.key_rotation_days}"
            )

        # Validate migration mode
        if self.migration_mode not in [e.value for e in MigrationMode]:
            raise SecurityPolicyError(
                f"Unsupported migration mode: {self.migration_mode}. "
                f"Supported: {[e.value for e in MigrationMode]}"
            )

        # Cross-validation
        if self.enabled:
            if not self.tamper_detection:
                raise SecurityPolicyError(
                    "tamper_detection must be enabled when encryption is enabled"
                )
            if not self.recovery_decryption:
                raise SecurityPolicyError(
                    "recovery_decryption must be enabled when encryption is enabled"
                )

    def get_effective_key_provider(self) -> str:
        """Get the effective key provider, resolving 'auto' based on platform."""
        if self.key_provider != KeyProvider.AUTO.value:
            return self.key_provider

        # Auto-detect based on platform
        if sys.platform == "darwin":
            return KeyProvider.KEYCHAIN.value
        elif os.name == "nt":
            return KeyProvider.CREDENTIAL_MANAGER.value
        else:  # Linux and others
            return KeyProvider.SECRET_SERVICE.value

    def should_rotate_keys(self) -> bool:
        """Check if key rotation is enabled."""
        return self.key_rotation_days > 0


@dataclass
class AuditCompatibilityConfig:
    """Configuration for backward compatibility and migration."""

    allow_plaintext_fallback: bool = True
    migration_timeout_seconds: int = 300
    max_migration_attempts: int = 3
    plaintext_retention_days: int = 30

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate()

    def _validate(self):
        """Validate the compatibility configuration."""
        if self.migration_timeout_seconds <= 0:
            raise SecurityPolicyError(
                f"migration_timeout_seconds must be positive, got: {self.migration_timeout_seconds}"
            )

        if self.max_migration_attempts <= 0:
            raise SecurityPolicyError(
                f"max_migration_attempts must be positive, got: {self.max_migration_attempts}"
            )

        if self.plaintext_retention_days < 0:
            raise SecurityPolicyError(
                f"plaintext_retention_days must be non-negative, got: {self.plaintext_retention_days}"
            )


@dataclass
class AuditConfig:
    """Complete audit configuration with encryption support."""

    # Legacy fields (v1.0 compatibility)
    log_all_validations: bool = True
    log_policy_decisions: bool = True
    require_justification: bool = False

    # New encryption configuration (v1.1)
    encryption: Optional[AuditEncryptionConfig] = None
    compatibility: Optional[AuditCompatibilityConfig] = None

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate()

    def _validate(self):
        """Validate the complete audit configuration."""
        # If encryption is configured, ensure it's valid
        if self.encryption is not None:
            # Cross-validate with legacy settings if needed
            pass

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditConfig":
        """Create AuditConfig from dictionary, handling backward compatibility."""
        # Extract legacy fields
        legacy_fields = {
            "log_all_validations": data.get("log_all_validations", True),
            "log_policy_decisions": data.get("log_policy_decisions", True),
            "require_justification": data.get("require_justification", False),
        }

        # Extract encryption configuration
        encryption_data = data.get("encryption")
        encryption_config = None
        if encryption_data is not None and isinstance(encryption_data, dict):
            encryption_config = AuditEncryptionConfig(**encryption_data)

        # Extract compatibility configuration
        compatibility_data = data.get("compatibility")
        compatibility_config = None
        if compatibility_data is not None and isinstance(compatibility_data, dict):
            compatibility_config = AuditCompatibilityConfig(**compatibility_data)

        return cls(
            **legacy_fields,
            encryption=encryption_config,
            compatibility=compatibility_config
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            # Legacy fields
            "log_all_validations": self.log_all_validations,
            "log_policy_decisions": self.log_policy_decisions,
            "require_justification": self.require_justification,
        }

        # Add encryption config if present
        if self.encryption is not None:
            result["encryption"] = asdict(self.encryption)

        # Add compatibility config if present
        if self.compatibility is not None:
            result["compatibility"] = asdict(self.compatibility)

        return result

    def is_encryption_enabled(self) -> bool:
        """Check if encryption is enabled."""
        return self.encryption is not None and self.encryption.enabled

    def get_encryption_config(self) -> Optional[AuditEncryptionConfig]:
        """Get the encryption configuration."""
        return self.encryption

    def get_compatibility_config(self) -> AuditCompatibilityConfig:
        """Get the compatibility configuration, creating defaults if needed."""
        if self.compatibility is None:
            self.compatibility = AuditCompatibilityConfig()
        return self.compatibility


class AuditEncryptionSchemaValidator:
    """Validator for audit encryption schema configurations."""

    @staticmethod
    def validate_schema(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate audit configuration schema.

        Args:
            data: The audit configuration dictionary

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        try:
            # Try to create the configuration - this will validate it
            config = AuditConfig.from_dict(data)
            return True, []

        except SecurityPolicyError as e:
            errors.append(str(e))
        except Exception as e:
            errors.append(f"Unexpected validation error: {e}")

        return False, errors

    @staticmethod
    def migrate_legacy_config(legacy_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate legacy audit configuration to new schema.

        Args:
            legacy_data: Legacy audit configuration

        Returns:
            Migrated configuration with new schema
        """
        # Create config from legacy data (will use defaults for new fields)
        config = AuditConfig.from_dict(legacy_data)

        # Convert back to dict for return
        return config.to_dict()

    @staticmethod
    def get_default_encryption_config() -> Dict[str, Any]:
        """Get default encryption configuration."""
        config = AuditConfig()
        # Force creation of encryption config with defaults
        if config.encryption is None:
            config.encryption = AuditEncryptionConfig()
        if config.compatibility is None:
            config.compatibility = AuditCompatibilityConfig()

        return config.to_dict()

    @staticmethod
    def detect_migration_needed(log_dir: Path) -> Tuple[bool, List[str]]:
        """
        Detect if migration is needed based on existing log files.

        Args:
            log_dir: Directory containing audit logs

        Returns:
            Tuple of (migration_needed, plaintext_files)
        """
        plaintext_files = []

        if not log_dir.exists():
            return False, []

        # Look for plaintext log files
        for log_file in log_dir.glob("*.log"):
            if log_file.stat().st_size > 0:  # Non-empty file
                plaintext_files.append(str(log_file))

        for json_file in log_dir.glob("*.jsonl"):
            if json_file.stat().st_size > 0:  # Non-empty file
                plaintext_files.append(str(json_file))

        return len(plaintext_files) > 0, plaintext_files


def validate_audit_config_schema(config_data: Dict[str, Any]) -> AuditConfig:
    """
    Validate and create AuditConfig from raw configuration data.

    Args:
        config_data: Raw audit configuration dictionary

    Returns:
        Validated AuditConfig instance

    Raises:
        SecurityPolicyError: If configuration is invalid
    """
    is_valid, errors = AuditEncryptionSchemaValidator.validate_schema(config_data)

    if not is_valid:
        error_msg = "Audit configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        raise SecurityPolicyError(error_msg)

    return AuditConfig.from_dict(config_data)


# Convenience functions for common operations
def is_encryption_enabled(audit_config: Dict[str, Any]) -> bool:
    """Check if encryption is enabled in audit configuration."""
    try:
        config = AuditConfig.from_dict(audit_config)
        return config.is_encryption_enabled()
    except:
        return False  # Default to disabled if config is invalid


def get_encryption_algorithm(audit_config: Dict[str, Any]) -> str:
    """Get the encryption algorithm from audit configuration."""
    try:
        config = AuditConfig.from_dict(audit_config)
        if config.encryption:
            return config.encryption.algorithm
        return EncryptionAlgorithm.AES_256_GCM.value
    except:
        return EncryptionAlgorithm.AES_256_GCM.value


def get_key_provider(audit_config: Dict[str, Any]) -> str:
    """Get the effective key provider from audit configuration."""
    try:
        config = AuditConfig.from_dict(audit_config)
        if config.encryption:
            return config.encryption.get_effective_key_provider()
        return KeyProvider.AUTO.value
    except:
        return KeyProvider.AUTO.value


# Export validation function for use in policy loading
__all__ = [
    "AuditConfig",
    "AuditEncryptionConfig",
    "AuditCompatibilityConfig",
    "AuditEncryptionSchemaValidator",
    "validate_audit_config_schema",
    "is_encryption_enabled",
    "get_encryption_algorithm",
    "get_key_provider",
    "EncryptionAlgorithm",
    "KeyProvider",
    "MigrationMode",
]