# Encrypted Audit Logging Schema Design

## Overview

This document outlines the expanded `security.audit` configuration schema to support AES-256-GCM encryption of audit logs at rest while maintaining backward compatibility with existing plaintext audit logs.

## Current Schema (v1.0)

```json
{
  "audit": {
    "log_all_validations": true,
    "log_policy_decisions": true,
    "require_justification": false
  }
}
```

## Expanded Schema (v1.1) - Backward Compatible

```json
{
  "audit": {
    // Legacy fields (maintained for backward compatibility)
    "log_all_validations": true,
    "log_policy_decisions": true,
    "require_justification": false,

    // New encryption configuration (v1.1)
    "encryption": {
      "enabled": true,                    // Default: true (secure by default)
      "algorithm": "AES-256-GCM",         // Only supported algorithm initially
      "key_provider": "auto",             // "auto", "keychain", "credential-manager", "secret-service", "custom"
      "key_rotation_days": 90,            // Days between key rotations (0 = disabled)
      "migration_mode": "auto",           // "auto", "manual", "disabled"
      "tamper_detection": true,           // Enable integrity verification
      "recovery_decryption": true         // Allow decryption for recovery workflows
    },

    // Migration and compatibility settings
    "compatibility": {
      "allow_plaintext_fallback": true,   // Allow reading plaintext logs during migration
      "migration_timeout_seconds": 300,  // Timeout for migration operations
      "max_migration_attempts": 3,        // Retry limit for failed migrations
      "plaintext_retention_days": 30     // Days to keep plaintext logs after encryption
    }
  }
}
```

## Schema Validation Rules

### Required Fields
- `encryption.enabled`: Must be boolean
- `encryption.algorithm`: Must be "AES-256-GCM" (only supported value initially)
- `encryption.key_provider`: Must be one of ["auto", "keychain", "credential-manager", "secret-service", "custom"]

### Conditional Validation
- If `encryption.enabled` is `true`:
  - `encryption.algorithm` must be specified
  - `encryption.key_provider` must be specified and valid for current platform
  - `encryption.tamper_detection` should be `true` (recommended)
  - `encryption.recovery_decryption` should be `true` (recommended)

- If `encryption.key_provider` is "auto":
  - Automatically selects appropriate provider based on platform:
    - macOS: "keychain"
    - Windows: "credential-manager"
    - Linux: "secret-service"

### Backward Compatibility
- All legacy fields (`log_all_validations`, `log_policy_decisions`, `require_justification`) are preserved
- If `encryption` section is missing, encryption is disabled (plaintext mode)
- Existing configurations without encryption settings continue to work unchanged

## Backward Compatibility Guarantees

### Schema Evolution
- **v1.0 → v1.1**: All existing audit configurations remain valid and functional
- **Legacy Field Preservation**: `log_all_validations`, `log_policy_decisions`, `require_justification` fields are maintained indefinitely
- **Graceful Degradation**: Invalid encryption configurations disable encryption rather than failing validation
- **Migration Safety**: Plaintext logs are preserved during migration with configurable retention periods

### Configuration Loading
- **TOML Compatibility**: Schema works with existing TOML-based configuration system
- **INI Migration**: Legacy INI configurations are automatically migrated without audit configuration loss
- **Validation Integration**: Audit schema validation is integrated into SecurityPolicy loading
- **Error Handling**: Invalid configurations provide clear error messages with remediation guidance

### Runtime Behavior
- **Default Security**: Encryption is enabled by default for new installations
- **Fallback Support**: Systems can read both encrypted and plaintext logs during migration
- **Recovery Options**: Manual decryption tools available for emergency recovery scenarios
- **Platform Agnostic**: Schema validation works consistently across all supported platforms

## Key Management References

### Platform-Specific Key Storage
- **macOS**: Keychain Service (`lazyscan.audit.encryption`)
- **Windows**: Credential Manager (`LazyScan/AuditEncryption`)
- **Linux**: Secret Service (DBus) with collection `lazyscan-audit`

### Key Derivation
- Master key: 256-bit AES key derived from user-provided passphrase or auto-generated
- Per-session keys: Derived from master key using HKDF with session-specific salt
- Key rotation: Automatic rotation with configurable intervals

## Migration Strategy

### Detection Logic
1. Check for existing plaintext audit files in log directory
2. Verify encryption configuration is enabled
3. Detect partially migrated state (mixed encrypted/plaintext files)

### Migration Process
1. **Phase 1**: Generate/retrieve encryption key from secure storage
2. **Phase 2**: Create encrypted backup of existing logs
3. **Phase 3**: Re-encrypt plaintext logs in chronological order
4. **Phase 4**: Update log rotation to use encryption
5. **Phase 5**: Cleanup plaintext logs after retention period

### Rollback Safeguards
- Maintain plaintext copies during migration
- Allow fallback to plaintext reading if decryption fails
- Provide manual decryption tools for recovery

## Error Handling and Validation

### Configuration Errors
- Invalid `key_provider` for platform → Fallback to "auto" with warning
- Missing encryption key → Generate new key with user notification
- Corrupted key storage → Alert user and disable encryption temporarily

### Runtime Errors
- Encryption failure → Log error and fallback to plaintext with alert
- Decryption failure → Attempt recovery decryption or alert security team
- Key rotation failure → Continue with current key and retry later

## Testing and Validation

### Schema Validation Tests
- Valid configurations for all platforms
- Invalid configurations with appropriate error messages
- Backward compatibility with v1.0 configurations
- Migration scenarios with various log states

### Integration Tests
- End-to-end encryption/decryption workflows
- Key rotation scenarios
- Migration from plaintext to encrypted logs
- Recovery decryption workflows

## Security Considerations

### Threat Model
- **Confidentiality**: Prevent unauthorized access to audit logs
- **Integrity**: Detect tampering of audit entries
- **Availability**: Ensure recovery workflows remain functional
- **Key Security**: Protect encryption keys from compromise

### Security Properties
- AES-256-GCM provides authenticated encryption
- Keys stored in platform-specific secure storage
- Tamper detection via GCM authentication tags
- Recovery decryption requires explicit authorization

## Implementation Plan

### Phase 1: Schema Design and Validation
- [x] Design expanded schema with backward compatibility
- [x] Implement schema validation logic
- [x] Add configuration migration helpers
- [x] Create unit tests for schema validation
- [x] Integrate validation into SecurityPolicy loading

### Phase 2: Key Management Infrastructure
- [ ] Implement platform-specific key providers
- [ ] Add key generation and storage logic
- [ ] Implement key rotation mechanisms
- [ ] Add key recovery workflows

### Phase 3: Encryption Pipeline Integration
- [ ] Modify AuditLogger to support encryption
- [ ] Implement encrypted log reading/writing
- [ ] Add tamper detection and integrity verification
- [ ] Update log rotation to handle encrypted files

### Phase 4: Migration and Recovery
- [ ] Implement migration detection and execution
- [ ] Add recovery decryption tools
- [ ] Create migration monitoring and rollback
- [ ] Update documentation and operational guides

### Phase 5: Testing and Validation
- [x] Comprehensive test suite for encryption features
- [x] CI validation hooks for schema compliance
- [ ] Performance benchmarking
- [ ] Security audit and penetration testing
- [ ] Documentation and training materials