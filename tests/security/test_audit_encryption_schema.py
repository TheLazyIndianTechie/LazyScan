#!/usr/bin/env python3
"""
Tests for audit encryption schema validation and configuration.
"""

import pytest
import json
from pathlib import Path

from lazyscan.security.audit_encryption_schema import (
    AuditConfig,
    AuditEncryptionConfig,
    AuditCompatibilityConfig,
    AuditEncryptionSchemaValidator,
    validate_audit_config_schema,
    is_encryption_enabled,
    get_encryption_algorithm,
    get_key_provider,
    EncryptionAlgorithm,
    KeyProvider,
    MigrationMode,
)
from lazyscan.core.errors import SecurityPolicyError


class TestAuditEncryptionConfig:
    """Test AuditEncryptionConfig dataclass."""

    def test_valid_config(self):
        """Test valid encryption configuration."""
        config = AuditEncryptionConfig(
            enabled=True,
            algorithm="AES-256-GCM",
            key_provider="auto",
            key_rotation_days=90,
            migration_mode="auto",
            tamper_detection=True,
            recovery_decryption=True
        )
        assert config.enabled is True
        assert config.algorithm == "AES-256-GCM"
        assert config.get_effective_key_provider() == "keychain"  # macOS

    def test_invalid_algorithm(self):
        """Test invalid encryption algorithm."""
        with pytest.raises(SecurityPolicyError, match="Unsupported encryption algorithm"):
            AuditEncryptionConfig(algorithm="INVALID-ALGO")

    def test_invalid_key_provider(self):
        """Test invalid key provider."""
        with pytest.raises(SecurityPolicyError, match="Unsupported key provider"):
            AuditEncryptionConfig(key_provider="invalid-provider")

    def test_negative_rotation_days(self):
        """Test negative key rotation days."""
        with pytest.raises(SecurityPolicyError, match="key_rotation_days must be non-negative"):
            AuditEncryptionConfig(key_rotation_days=-1)

    def test_invalid_migration_mode(self):
        """Test invalid migration mode."""
        with pytest.raises(SecurityPolicyError, match="Unsupported migration mode"):
            AuditEncryptionConfig(migration_mode="invalid")

    def test_encryption_without_tamper_detection(self):
        """Test encryption enabled without tamper detection."""
        with pytest.raises(SecurityPolicyError, match="tamper_detection must be enabled"):
            AuditEncryptionConfig(enabled=True, tamper_detection=False)

    def test_encryption_without_recovery_decryption(self):
        """Test encryption enabled without recovery decryption."""
        with pytest.raises(SecurityPolicyError, match="recovery_decryption must be enabled"):
            AuditEncryptionConfig(enabled=True, recovery_decryption=False)

    def test_key_provider_resolution(self):
        """Test key provider auto-resolution."""
        config = AuditEncryptionConfig(key_provider="auto")

        # Test effective provider (depends on platform)
        effective = config.get_effective_key_provider()
        assert effective in ["keychain", "credential-manager", "secret-service"]

    def test_key_rotation_enabled(self):
        """Test key rotation detection."""
        assert AuditEncryptionConfig(key_rotation_days=90).should_rotate_keys() is True
        assert AuditEncryptionConfig(key_rotation_days=0).should_rotate_keys() is False


class TestAuditCompatibilityConfig:
    """Test AuditCompatibilityConfig dataclass."""

    def test_valid_config(self):
        """Test valid compatibility configuration."""
        config = AuditCompatibilityConfig(
            allow_plaintext_fallback=True,
            migration_timeout_seconds=300,
            max_migration_attempts=3,
            plaintext_retention_days=30
        )
        assert config.allow_plaintext_fallback is True
        assert config.migration_timeout_seconds == 300

    def test_invalid_timeout(self):
        """Test invalid migration timeout."""
        with pytest.raises(SecurityPolicyError, match="migration_timeout_seconds must be positive"):
            AuditCompatibilityConfig(migration_timeout_seconds=0)

    def test_invalid_attempts(self):
        """Test invalid max migration attempts."""
        with pytest.raises(SecurityPolicyError, match="max_migration_attempts must be positive"):
            AuditCompatibilityConfig(max_migration_attempts=0)

    def test_negative_retention_days(self):
        """Test negative plaintext retention days."""
        with pytest.raises(SecurityPolicyError, match="plaintext_retention_days must be non-negative"):
            AuditCompatibilityConfig(plaintext_retention_days=-1)


class TestAuditConfig:
    """Test AuditConfig dataclass."""

    def test_legacy_config_only(self):
        """Test configuration with only legacy fields."""
        data = {
            "log_all_validations": True,
            "log_policy_decisions": False,
            "require_justification": True
        }

        config = AuditConfig.from_dict(data)
        assert config.log_all_validations is True
        assert config.log_policy_decisions is False
        assert config.require_justification is True
        assert config.encryption is None
        assert config.compatibility is None
        assert config.is_encryption_enabled() is False

    def test_full_config(self):
        """Test complete configuration with encryption."""
        data = {
            "log_all_validations": True,
            "log_policy_decisions": True,
            "require_justification": False,
            "encryption": {
                "enabled": True,
                "algorithm": "AES-256-GCM",
                "key_provider": "auto",
                "key_rotation_days": 90,
                "migration_mode": "auto",
                "tamper_detection": True,
                "recovery_decryption": True
            },
            "compatibility": {
                "allow_plaintext_fallback": True,
                "migration_timeout_seconds": 300,
                "max_migration_attempts": 3,
                "plaintext_retention_days": 30
            }
        }

        config = AuditConfig.from_dict(data)
        assert config.is_encryption_enabled() is True
        assert config.encryption.algorithm == "AES-256-GCM"
        assert config.compatibility.allow_plaintext_fallback is True

    def test_serialization(self):
        """Test configuration serialization."""
        config = AuditConfig(
            log_all_validations=False,
            encryption=AuditEncryptionConfig(enabled=True),
            compatibility=AuditCompatibilityConfig()
        )

        data = config.to_dict()
        assert data["log_all_validations"] is False
        assert "encryption" in data
        assert "compatibility" in data

        # Test round-trip
        config2 = AuditConfig.from_dict(data)
        assert config2.log_all_validations is False
        assert config2.is_encryption_enabled() is True


class TestAuditEncryptionSchemaValidator:
    """Test schema validation functionality."""

    def test_valid_schema(self):
        """Test valid schema validation."""
        data = {
            "log_all_validations": True,
            "log_policy_decisions": True,
            "require_justification": False,
            "encryption": {
                "enabled": True,
                "algorithm": "AES-256-GCM",
                "key_provider": "auto",
                "key_rotation_days": 90,
                "migration_mode": "auto",
                "tamper_detection": True,
                "recovery_decryption": True
            }
        }

        is_valid, errors = AuditEncryptionSchemaValidator.validate_schema(data)
        assert is_valid is True
        assert len(errors) == 0

    def test_invalid_schema(self):
        """Test invalid schema validation."""
        data = {
            "log_all_validations": True,
            "encryption": {
                "enabled": True,
                "algorithm": "INVALID-ALGO"  # Invalid algorithm
            }
        }

        is_valid, errors = AuditEncryptionSchemaValidator.validate_schema(data)
        assert is_valid is False
        assert len(errors) > 0
        assert "Unsupported encryption algorithm" in str(errors[0])

    def test_legacy_migration(self):
        """Test legacy configuration migration."""
        legacy_data = {
            "log_all_validations": True,
            "log_policy_decisions": False,
            "require_justification": True
        }

        migrated = AuditEncryptionSchemaValidator.migrate_legacy_config(legacy_data)

        # Should preserve legacy fields
        assert migrated["log_all_validations"] is True
        assert migrated["log_policy_decisions"] is False
        assert migrated["require_justification"] is True

        # Should not add encryption by default
        assert "encryption" not in migrated

    def test_default_encryption_config(self):
        """Test default encryption configuration."""
        default_config = AuditEncryptionSchemaValidator.get_default_encryption_config()

        assert "encryption" in default_config
        assert "compatibility" in default_config
        assert default_config["encryption"]["enabled"] is True
        assert default_config["encryption"]["algorithm"] == "AES-256-GCM"

    def test_migration_detection(self, tmp_path):
        """Test migration detection logic."""
        log_dir = tmp_path / "logs"
        log_dir.mkdir()

        # No files - no migration needed
        needed, files = AuditEncryptionSchemaValidator.detect_migration_needed(log_dir)
        assert needed is False
        assert len(files) == 0

        # Create plaintext log file
        log_file = log_dir / "audit.log"
        log_file.write_text("test log entry")

        needed, files = AuditEncryptionSchemaValidator.detect_migration_needed(log_dir)
        assert needed is True
        assert str(log_file) in files

        # Create JSON log file
        json_file = log_dir / "audit.jsonl"
        json_file.write_text('{"test": "data"}')

        needed, files = AuditEncryptionSchemaValidator.detect_migration_needed(log_dir)
        assert needed is True
        assert len(files) == 2


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_is_encryption_enabled(self):
        """Test is_encryption_enabled function."""
        # No encryption config
        config = {"log_all_validations": True}
        assert is_encryption_enabled(config) is False

        # Encryption disabled
        config = {
            "encryption": {"enabled": False, "algorithm": "AES-256-GCM"}
        }
        assert is_encryption_enabled(config) is False

        # Encryption enabled
        config = {
            "encryption": {"enabled": True, "algorithm": "AES-256-GCM"}
        }
        assert is_encryption_enabled(config) is True

    def test_get_encryption_algorithm(self):
        """Test get_encryption_algorithm function."""
        # Default when no config
        config = {}
        assert get_encryption_algorithm(config) == "AES-256-GCM"

        # From config
        config = {"encryption": {"algorithm": "AES-256-GCM"}}
        assert get_encryption_algorithm(config) == "AES-256-GCM"

    def test_get_key_provider(self):
        """Test get_key_provider function."""
        # Default when no config
        config = {}
        assert get_key_provider(config) == "auto"

        # From config
        config = {"encryption": {"key_provider": "keychain"}}
        assert get_key_provider(config) == "keychain"


class TestValidateAuditConfigSchema:
    """Test the main validation function."""

    def test_valid_config(self):
        """Test valid configuration validation."""
        config_data = {
            "log_all_validations": True,
            "log_policy_decisions": True,
            "require_justification": False,
            "encryption": {
                "enabled": True,
                "algorithm": "AES-256-GCM",
                "key_provider": "auto",
                "key_rotation_days": 90,
                "migration_mode": "auto",
                "tamper_detection": True,
                "recovery_decryption": True
            }
        }

        config = validate_audit_config_schema(config_data)
        assert isinstance(config, AuditConfig)
        assert config.is_encryption_enabled() is True

    def test_invalid_config(self):
        """Test invalid configuration validation."""
        config_data = {
            "encryption": {
                "enabled": True,
                "algorithm": "INVALID-ALGO"
            }
        }

        with pytest.raises(SecurityPolicyError, match="Audit configuration validation failed"):
            validate_audit_config_schema(config_data)


class TestBackwardCompatibility:
    """Test backward compatibility scenarios."""

    def test_v1_0_config_compatibility(self):
        """Test that v1.0 configurations work unchanged."""
        v1_config = {
            "log_all_validations": True,
            "log_policy_decisions": True,
            "require_justification": False
        }

        # Should validate successfully
        config = validate_audit_config_schema(v1_config)
        assert config.log_all_validations is True
        assert config.is_encryption_enabled() is False

    def test_partial_encryption_config(self):
        """Test configuration with partial encryption settings."""
        config_data = {
            "log_all_validations": True,
            "encryption": {
                "enabled": False  # Minimal encryption config
            }
        }

        config = validate_audit_config_schema(config_data)
        assert config.is_encryption_enabled() is False

    def test_malformed_encryption_config(self):
        """Test handling of malformed encryption configuration."""
        config_data = {
            "log_all_validations": True,
            "encryption": "not_a_dict"  # Invalid encryption config
        }

        # Should handle gracefully (encryption disabled)
        config = validate_audit_config_schema(config_data)
        assert config.is_encryption_enabled() is False


class TestSecurityPolicyIntegration:
    """Test integration with SecurityPolicy validation."""

    def test_policy_with_valid_audit_config(self):
        """Test that SecurityPolicy validates audit configuration."""
        from lazyscan.security.sentinel import SecurityPolicy
        import json
        from pathlib import Path

        # Load default policy which has valid audit config
        default_policy_path = Path(__file__).parent.parent.parent / "lazyscan" / "security" / "default_policy.json"
        with open(default_policy_path, "r") as f:
            policy_data = json.load(f)

        # Should validate successfully
        policy = SecurityPolicy(policy_data)
        assert policy.audit is not None
        assert isinstance(policy.audit, dict)

    def test_policy_with_invalid_audit_config(self):
        """Test that SecurityPolicy rejects invalid audit configuration."""
        from lazyscan.security.sentinel import SecurityPolicy, SecurityPolicyError

        policy_data = {
            "version": "1.0",
            "behavior_flags": {
                "require_trash_first": True,
                "interactive_double_confirm": True,
                "block_symlinks": True
            },
            "size_limits": {
                "large_directory_threshold_mb": 100,
                "max_deletion_size_mb": 10000
            },
            "allowed_roots": {},
            "deny_patterns": {
                "macos": [],
                "windows": [],
                "linux": []
            },
            "audit": {
                "log_all_validations": True,
                "encryption": {
                    "enabled": True,
                    "algorithm": "INVALID-ALGO"  # Invalid algorithm
                }
            }
        }

        # Should raise SecurityPolicyError due to invalid audit config
        with pytest.raises(SecurityPolicyError, match="Audit configuration validation failed"):
            SecurityPolicy(policy_data)