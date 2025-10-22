# Security Integration Guide for LazyScan

This guide explains how to integrate the comprehensive security framework into the main LazyScan application to prevent accidental data deletion and ensure safe operations.

## Overview

The security framework consists of five main components:

1. **Path Validation** (`helpers/security.py`) - Prevents path traversal attacks
2. **Confirmation Dialogs** (`helpers/confirmation.py`) - Multi-level user confirmations
3. **Audit Logging** (`helpers/audit.py`) - Comprehensive operation tracking
4. **Secure Operations** (`helpers/secure_operations.py`) - Safe operation wrappers
5. **Recovery System** (`helpers/recovery.py`) - Undo and restore functionality

## Quick Integration

### 1. Replace Unsafe Operations

Replace direct file operations in `lazyscan.py` with secure wrappers:

```python
# OLD - Unsafe direct deletion
def delete_cache_files(paths):
    for path in paths:
        if os.path.exists(path):
            if os.path.isfile(path):
                os.remove(path)
            else:
                shutil.rmtree(path)

# NEW - Secure deletion with full safety measures
from helpers.secure_operations import secure_delete

def delete_cache_files(paths):
    result = secure_delete(paths, "Cache Cleanup")
    if result.success:
        print(f"✅ Successfully deleted {result.files_processed} files ({result.size_processed} bytes)")
        if result.backup_paths:
            print(f"🔄 Backups created: {len(result.backup_paths)} locations")
    else:
        print(f"❌ Deletion failed: {result.message}")
        for error in result.errors:
            print(f"   Error: {error}")
    return result
```

### 2. Secure Directory Scanning

Replace direct directory scanning with validated scanning:

```python
# OLD - Direct scanning
def scan_directory(directory):
    total_size = 0
    file_count = 0
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            total_size += os.path.getsize(file_path)
            file_count += 1
    return {"total_size": total_size, "file_count": file_count}

# NEW - Secure scanning with validation
from helpers.secure_operations import secure_scan

def scan_directory(directory):
    def scan_function(dir_path):
        total_size = 0
        file_count = 0
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                try:
                    file_path = os.path.join(root, file)
                    total_size += os.path.getsize(file_path)
                    file_count += 1
                except (OSError, IOError):
                    continue
        return {"total_size": total_size, "file_count": file_count}

    result = secure_scan(directory, scan_function)
    if result.success:
        return result.details
    else:
        print(f"❌ Scan failed: {result.message}")
        return {"total_size": 0, "file_count": 0}
```

### 3. Add Recovery Menu

Add recovery options to the main menu:

```python
from helpers.recovery import list_recent_operations, recovery_manager

def show_recovery_menu():
    """Display recovery options to user"""
    recent_ops = list_recent_operations(days_back=7)

    if not recent_ops:
        print("\n📋 No recent operations available for recovery.")
        return

    print("\n🔄 Recent Operations (Recoverable):")
    print("=" * 50)

    recoverable_ops = [op for op in recent_ops if op['can_recover']]

    if not recoverable_ops:
        print("No operations can be recovered at this time.")
        return

    for i, op in enumerate(recoverable_ops, 1):
        timestamp = datetime.fromisoformat(op['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
        size_mb = op['size_affected'] / (1024 * 1024)
        print(f"{i}. {op['operation_type']}")
        print(f"   Time: {timestamp}")
        print(f"   Files: {op['files_affected']:,} ({size_mb:.1f} MB)")
        print(f"   Status: {op['recovery_status']}")
        print()

    try:
        choice = input("Enter operation number to recover (or 'q' to quit): ").strip()
        if choice.lower() == 'q':
            return

        choice_idx = int(choice) - 1
        if 0 <= choice_idx < len(recoverable_ops):
            selected_op = recoverable_ops[choice_idx]

            print(f"\n🔄 Recovering: {selected_op['operation_type']}")
            print("This will restore all deleted files from backups.")

            confirm = input("Continue with recovery? (y/N): ").strip().lower()
            if confirm == 'y':
                result = recovery_manager.undo_operation(selected_op['operation_id'])

                if result.success:
                    print(f"\n✅ Recovery completed successfully!")
                    print(f"   Files restored: {result.files_restored:,}")
                    print(f"   Size restored: {result.size_restored / (1024*1024):.1f} MB")
                    if result.warnings:
                        print("   Warnings:")
                        for warning in result.warnings:
                            print(f"     - {warning}")
                else:
                    print(f"\n❌ Recovery failed: {result.message}")
                    if result.failed_paths:
                        print(f"   Failed paths: {len(result.failed_paths)}")
            else:
                print("Recovery cancelled.")
        else:
            print("Invalid selection.")

    except (ValueError, IndexError):
        print("Invalid input.")
```

### 4. Initialize Security System

Add initialization code to the main application:

```python
# Add to the beginning of lazyscan.py
from helpers.audit import audit_logger, EventType, Severity
from helpers.secure_operations import configure_security
from helpers.recovery import get_recovery_stats

def initialize_security_system():
    """Initialize the security framework"""
    # Log application startup
    audit_logger.log_startup({
        "version": "0.5.0",
        "security_enabled": True,
        "backup_enabled": True
    })

    # Configure security settings
    configure_security(enable_backups=True, enable_confirmations=True)

    # Show recovery statistics
    stats = get_recovery_stats()
    if stats['recoverable_operations'] > 0:
        print(f"\n🔄 Recovery System: {stats['recoverable_operations']} operations can be recovered")
        print(f"   Total recoverable: {stats['total_files_recoverable']:,} files ({stats['total_size_recoverable'] / (1024**3):.1f} GB)")

# Call during application startup
if __name__ == "__main__":
    initialize_security_system()
    # ... rest of main application
```

### 5. Update Main Menu

Add security options to the main menu:

```python
def show_main_menu():
    print("\n" + "=" * 60)
    print("                    🧹 LazyScan v0.5.0")
    print("                 Secure Cache Cleaner")
    print("=" * 60)
    print("\n📁 Scan Options:")
    print("1. Scan Chrome Cache")
    print("2. Scan Unity Cache")
    print("3. Scan Unreal Engine Cache")
    print("4. Scan macOS System Cache")
    print("5. Custom Directory Scan")
    print("\n🗑️  Cleanup Options:")
    print("6. Clean Selected Caches")
    print("7. Clean All Detected Caches")
    print("\n🔄 Recovery Options:")
    print("8. View Recent Operations")
    print("9. Recover Deleted Files")
    print("10. Recovery Statistics")
    print("\n⚙️  Settings:")
    print("11. Security Settings")
    print("12. View Audit Logs")
    print("\n0. Exit")
    print("\n" + "=" * 60)

def handle_menu_choice(choice):
    if choice == "8":
        show_recent_operations()
    elif choice == "9":
        show_recovery_menu()
    elif choice == "10":
        show_recovery_statistics()
    elif choice == "11":
        show_security_settings()
    elif choice == "12":
        show_audit_logs()
    # ... handle other choices
```

## Advanced Integration

### Custom Risk Assessment

Customize risk levels for your specific use case:

```python
from helpers.confirmation import ConfirmationDialog, RiskLevel

# Create custom confirmation dialog with specific rules
confirmation = ConfirmationDialog()

# Add custom risk assessment
def assess_custom_risk(paths, total_size, file_count):
    # Custom logic for your application
    if any("important" in path.lower() for path in paths):
        return RiskLevel.CRITICAL
    elif total_size > 10 * 1024**3:  # > 10GB
        return RiskLevel.HIGH
    elif file_count > 10000:
        return RiskLevel.MEDIUM
    else:
        return RiskLevel.LOW

# Use custom risk assessment
confirmation.risk_assessor = assess_custom_risk
```

### Custom Backup Strategies

Implement application-specific backup strategies:

```python
from helpers.security import BackupManager

class CustomBackupManager(BackupManager):
    def create_backup(self, source_path, operation_id=None):
        # Custom backup logic
        # For example, only backup certain file types
        if self.should_backup(source_path):
            return super().create_backup(source_path, operation_id)
        return None

    def should_backup(self, path):
        # Custom logic to determine if path should be backed up
        important_extensions = ['.config', '.plist', '.json', '.xml']
        if os.path.isfile(path):
            _, ext = os.path.splitext(path)
            return ext.lower() in important_extensions
        return True  # Always backup directories
```

### Integration Testing

Test the security integration:

```python
def test_security_integration():
    """Test security framework integration"""
    from helpers.secure_operations import secure_delete, secure_scan
    from helpers.recovery import recovery_manager
    import tempfile

    # Create test directory
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("Test content")

        # Test secure scan
        scan_result = secure_scan(temp_dir, lambda d: {"total_size": 100, "file_count": 1})
        assert scan_result.success, "Secure scan should succeed"

        # Test secure delete with recovery
        delete_result = secure_delete([test_file], "Test Deletion")
        assert delete_result.success, "Secure delete should succeed"
        assert len(delete_result.backup_paths) > 0, "Backup should be created"

        # Test recovery
        recovery_result = recovery_manager.undo_operation(delete_result.operation_id)
        assert recovery_result.success, "Recovery should succeed"
        assert os.path.exists(test_file), "File should be restored"

        print("✅ Security integration test passed!")

if __name__ == "__main__":
    test_security_integration()
```

## Configuration

### Environment Variables

Configure security settings via environment variables:

```python
import os
from helpers.secure_operations import configure_security

# Configure based on environment
ENABLE_BACKUPS = os.getenv('LAZYSCAN_ENABLE_BACKUPS', 'true').lower() == 'true'
ENABLE_CONFIRMATIONS = os.getenv('LAZYSCAN_ENABLE_CONFIRMATIONS', 'true').lower() == 'true'
RECOVERY_RETENTION_DAYS = int(os.getenv('LAZYSCAN_RECOVERY_RETENTION_DAYS', '30'))

configure_security(enable_backups=ENABLE_BACKUPS, enable_confirmations=ENABLE_CONFIRMATIONS)
```

### Configuration File

Create a configuration file for security settings:

```python
# config.py
SECURITY_CONFIG = {
    'enable_backups': True,
    'enable_confirmations': True,
    'backup_retention_days': 30,
    'max_backup_size_gb': 50,
    'require_confirmation_above_gb': 1,
    'critical_paths': [
        '/System',
        '/usr/bin',
        '/Applications',
    ],
    'allowed_cache_keywords': [
        'cache', 'temp', 'tmp', 'log', 'logs',
        'intermediate', 'derived', 'build'
    ]
}
```

## Best Practices

1. **Always use secure wrappers** - Never bypass the security framework
2. **Test recovery regularly** - Ensure backups are working correctly
3. **Monitor audit logs** - Review logs for suspicious activity
4. **Configure appropriate risk levels** - Adjust confirmation requirements
5. **Clean up old recovery records** - Prevent disk space issues
6. **Validate user input** - Always sanitize paths and selections
7. **Handle errors gracefully** - Provide clear error messages
8. **Document security decisions** - Log why certain operations were allowed/blocked

## Troubleshooting

### Common Issues

1. **Permission Errors**: Ensure the application has appropriate file system permissions
2. **Backup Failures**: Check available disk space and backup directory permissions
3. **Recovery Failures**: Verify backup integrity and original path availability
4. **Path Validation Errors**: Review allowed/forbidden path configurations

### Debug Mode

Enable debug logging for troubleshooting:

```python
from helpers.audit import audit_logger
import logging

# Enable debug logging
logging.getLogger().setLevel(logging.DEBUG)
audit_logger.logger.setLevel(logging.DEBUG)
```

## Security Considerations

1. **Backup Security**: Backups contain sensitive data - ensure proper permissions
2. **Log Security**: Audit logs may contain sensitive paths - protect access
3. **Recovery Security**: Verify backup integrity before restoration
4. **Path Traversal**: The framework prevents most attacks, but validate custom paths
5. **Privilege Escalation**: Never run with unnecessary elevated privileges

This integration guide provides a comprehensive approach to securing LazyScan operations while maintaining usability and providing robust recovery capabilities.
