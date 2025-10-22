#!/usr/bin/env python3
"""
Secure Operations Wrapper for LazyScan

This module provides secure wrappers for all LazyScan operations,
integrating path validation, confirmation dialogs, backup systems,
and audit logging to ensure safe execution.

Author: Security Enhancement for LazyScan
Version: 1.0.0
"""

import os
import shutil
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Optional

from .audit import (
    EventType,
    Severity,
    log_backup,
    log_delete,
    log_scan,
    log_security_violation,
    log_user_confirmation,
)
from .confirmation import (
    ConfirmationDialog,
    PermissionChecker,
    check_permissions,
    determine_risk_level,
    get_confirmation,
)

# Import security modules
from .security import (
    BackupManager,
    InputSanitizer,
    PathValidator,
    create_backup,
    sanitize_input,
    validate_path,
    validate_paths,
)


@dataclass
class OperationResult:
    """Result of a secure operation"""

    success: bool
    message: str
    details: dict[str, Any]
    files_processed: int = 0
    size_processed: int = 0
    errors: list[str] = None
    warnings: list[str] = None
    backup_paths: list[str] = None
    operation_id: str = None
    duration: float = 0.0

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.backup_paths is None:
            self.backup_paths = []
        if self.operation_id is None:
            self.operation_id = str(uuid.uuid4())[:8]


class SecureOperationManager:
    """
    Secure operation manager that wraps all LazyScan operations
    with comprehensive safety measures.
    """

    def __init__(self, enable_backups: bool = True, enable_confirmations: bool = True):
        self.path_validator = PathValidator()
        self.input_sanitizer = InputSanitizer()
        self.backup_manager = BackupManager()
        self.confirmation_dialog = ConfirmationDialog()
        self.permission_checker = PermissionChecker()

        self.enable_backups = enable_backups
        self.enable_confirmations = enable_confirmations

        # Operation tracking
        self.active_operations = {}
        self.operation_history = []

    @contextmanager
    def secure_operation(self, operation_name: str, paths: list[str]):
        """Context manager for secure operations with full audit trail"""
        operation_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        # Log operation start
        from .audit import audit_logger

        audit_logger.log_event(
            (
                EventType.SCAN_START
                if "scan" in operation_name.lower()
                else EventType.DELETE_START
            ),
            Severity.INFO,
            f"Starting {operation_name}",
            {
                "operation_id": operation_id,
                "paths_count": len(paths),
                "paths": paths[:5],  # First 5 paths
            },
        )

        self.active_operations[operation_id] = {
            "name": operation_name,
            "paths": paths,
            "start_time": start_time,
            "status": "running",
        }

        try:
            yield operation_id

        except Exception as e:
            # Log operation failure
            audit_logger.log_event(
                EventType.ERROR,
                Severity.ERROR,
                f"Operation {operation_name} failed: {e!s}",
                {
                    "operation_id": operation_id,
                    "error": str(e),
                    "duration": time.time() - start_time,
                },
            )
            raise

        finally:
            # Clean up operation tracking
            if operation_id in self.active_operations:
                operation = self.active_operations.pop(operation_id)
                operation["duration"] = time.time() - start_time
                operation["status"] = "completed"
                self.operation_history.append(operation)

    def secure_scan_directory(
        self, directory_path: str, scan_function: Callable[[str], dict[str, Any]]
    ) -> OperationResult:
        """
        Securely scan a directory with full validation and logging.

        Args:
            directory_path: Path to scan
            scan_function: Function that performs the actual scanning

        Returns:
            OperationResult: Results of the scan operation
        """
        start_time = time.time()

        # Sanitize input
        directory_path = sanitize_input(directory_path, "path")

        # Validate path
        is_safe, reason = validate_path(directory_path)
        if not is_safe:
            log_security_violation(
                f"Unsafe path in scan operation: {directory_path}",
                {
                    "type": "path_validation",
                    "path": directory_path,
                    "reason": reason,
                    "blocked": True,
                },
            )
            return OperationResult(
                success=False,
                message=f"Security validation failed: {reason}",
                details={"path": directory_path, "validation_error": reason},
            )

        # Check permissions
        has_permission, permission_errors = check_permissions([directory_path])
        if not has_permission:
            return OperationResult(
                success=False,
                message="Insufficient permissions",
                details={"permission_errors": permission_errors},
                errors=permission_errors,
            )

        # Add to allowed roots for this session
        self.path_validator.add_allowed_root(directory_path)

        try:
            with self.secure_operation(
                "Directory Scan", [directory_path]
            ) as operation_id:
                # Perform the scan
                scan_results = scan_function(directory_path)

                duration = time.time() - start_time

                # Log successful scan
                log_scan(
                    "directory_scan",
                    [directory_path],
                    {
                        "total_size": scan_results.get("total_size", 0),
                        "file_count": scan_results.get("file_count", 0),
                        "duration": duration,
                    },
                )

                return OperationResult(
                    success=True,
                    message="Scan completed successfully",
                    details=scan_results,
                    files_processed=scan_results.get("file_count", 0),
                    size_processed=scan_results.get("total_size", 0),
                    operation_id=operation_id,
                    duration=duration,
                )

        except Exception as e:
            return OperationResult(
                success=False,
                message=f"Scan operation failed: {e!s}",
                details={"error": str(e), "path": directory_path},
                errors=[str(e)],
                duration=time.time() - start_time,
            )

    def secure_delete_paths(
        self, paths: list[str], operation_type: str = "Cache Cleanup"
    ) -> OperationResult:
        """
        Securely delete paths with full validation, confirmation, and backup.

        Args:
            paths: List of paths to delete
            operation_type: Description of the operation

        Returns:
            OperationResult: Results of the deletion operation
        """
        start_time = time.time()
        operation_id = str(uuid.uuid4())[:8]

        # Sanitize all paths
        sanitized_paths = [sanitize_input(path, "path") for path in paths]

        # Validate all paths
        validation_results = validate_paths(sanitized_paths)
        unsafe_paths = [
            path for path, (is_safe, _) in validation_results.items() if not is_safe
        ]

        if unsafe_paths:
            # Log security violation
            for unsafe_path in unsafe_paths:
                _, reason = validation_results[unsafe_path]
                log_security_violation(
                    f"Unsafe path in delete operation: {unsafe_path}",
                    {
                        "type": "path_validation",
                        "path": unsafe_path,
                        "reason": reason,
                        "blocked": True,
                    },
                )

            return OperationResult(
                success=False,
                message=f"Security validation failed for {len(unsafe_paths)} paths",
                details={
                    "unsafe_paths": unsafe_paths,
                    "validation_results": validation_results,
                },
                errors=[f"Unsafe path: {path}" for path in unsafe_paths],
            )

        # Check permissions
        has_permission, permission_errors = check_permissions(sanitized_paths)
        if not has_permission:
            return OperationResult(
                success=False,
                message="Insufficient permissions for deletion",
                details={"permission_errors": permission_errors},
                errors=permission_errors,
            )

        # Calculate operation statistics
        total_size = 0
        file_count = 0
        existing_paths = []

        for path in sanitized_paths:
            if os.path.exists(path):
                existing_paths.append(path)
                if os.path.isfile(path):
                    total_size += os.path.getsize(path)
                    file_count += 1
                else:
                    # Directory - calculate size
                    for root, dirs, files in os.walk(path):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                total_size += os.path.getsize(file_path)
                                file_count += 1
                            except OSError:
                                continue

        if not existing_paths:
            return OperationResult(
                success=True,
                message="No existing paths to delete",
                details={"original_paths": paths, "existing_paths": existing_paths},
            )

        # Get user confirmation if enabled
        if self.enable_confirmations:
            warnings = []

            # Add warnings for large operations
            if total_size > 5 * 1024**3:  # > 5GB
                warnings.append(f"Large deletion: {total_size / (1024**3):.1f} GB")
            if file_count > 50000:
                warnings.append(f"Many files: {file_count:,} files")

            confirmed = get_confirmation(
                operation_type, existing_paths, total_size, file_count, warnings
            )

            # Log user decision
            log_user_confirmation(
                operation_type,
                confirmed,
                {
                    "risk_level": determine_risk_level(
                        existing_paths, total_size, file_count
                    ).value,
                    "paths_count": len(existing_paths),
                    "total_size": total_size,
                    "confirmation_method": "interactive",
                },
            )

            if not confirmed:
                return OperationResult(
                    success=False,
                    message="Operation cancelled by user",
                    details={"user_cancelled": True, "paths": existing_paths},
                )

        # Create backups if enabled
        backup_paths = []
        if self.enable_backups:
            print("\n🔄 Creating backups before deletion...")
            for path in existing_paths:
                try:
                    backup_path = create_backup(path, operation_id)
                    if backup_path:
                        backup_paths.append(backup_path)
                        log_backup(
                            path, backup_path, True, {"size": self._get_path_size(path)}
                        )
                    else:
                        log_backup(path, "", False, {"error": "Backup creation failed"})
                except Exception as e:
                    log_backup(path, "", False, {"error": str(e)})
                    return OperationResult(
                        success=False,
                        message=f"Backup failed for {path}: {e!s}",
                        details={"backup_error": str(e), "path": path},
                        errors=[f"Backup failed: {e!s}"],
                    )

        # Perform deletion
        deleted_files = 0
        deleted_size = 0
        errors = []

        try:
            with self.secure_operation(
                f"Delete Operation: {operation_type}", existing_paths
            ) as op_id:
                for path in existing_paths:
                    try:
                        if os.path.isfile(path):
                            size = os.path.getsize(path)
                            os.remove(path)
                            deleted_files += 1
                            deleted_size += size
                        elif os.path.isdir(path):
                            # Count files before deletion
                            dir_files = 0
                            dir_size = 0
                            for root, dirs, files in os.walk(path):
                                for file in files:
                                    try:
                                        file_path = os.path.join(root, file)
                                        dir_size += os.path.getsize(file_path)
                                        dir_files += 1
                                    except OSError:
                                        continue

                            shutil.rmtree(path)
                            deleted_files += dir_files
                            deleted_size += dir_size

                    except Exception as e:
                        error_msg = f"Failed to delete {path}: {e!s}"
                        errors.append(error_msg)
                        continue

                duration = time.time() - start_time

                # Log deletion results
                log_delete(
                    existing_paths,
                    len(errors) == 0,
                    {
                        "files_deleted": deleted_files,
                        "size_freed": deleted_size,
                        "errors": errors,
                        "duration": duration,
                    },
                )

                success = len(errors) == 0
                message = (
                    "Deletion completed successfully"
                    if success
                    else f"Deletion completed with {len(errors)} errors"
                )

                return OperationResult(
                    success=success,
                    message=message,
                    details={
                        "paths_targeted": len(existing_paths),
                        "files_deleted": deleted_files,
                        "size_freed": deleted_size,
                        "backups_created": len(backup_paths),
                    },
                    files_processed=deleted_files,
                    size_processed=deleted_size,
                    errors=errors,
                    backup_paths=backup_paths,
                    operation_id=op_id,
                    duration=duration,
                )

        except Exception as e:
            # Critical error during deletion
            error_msg = f"Critical error during deletion: {e!s}"
            log_delete(
                existing_paths,
                False,
                {"critical_error": str(e), "duration": time.time() - start_time},
            )

            return OperationResult(
                success=False,
                message=error_msg,
                details={"critical_error": str(e)},
                errors=[error_msg],
                backup_paths=backup_paths,
                operation_id=operation_id,
                duration=time.time() - start_time,
            )

    def _get_path_size(self, path: str) -> int:
        """Get size of file or directory"""
        if os.path.isfile(path):
            return os.path.getsize(path)
        elif os.path.isdir(path):
            total = 0
            for root, dirs, files in os.walk(path):
                for file in files:
                    try:
                        total += os.path.getsize(os.path.join(root, file))
                    except OSError:
                        continue
            return total
        return 0

    def get_operation_status(self, operation_id: str) -> Optional[dict[str, Any]]:
        """Get status of an operation"""
        if operation_id in self.active_operations:
            return self.active_operations[operation_id]

        for operation in self.operation_history:
            if operation.get("operation_id") == operation_id:
                return operation

        return None

    def list_active_operations(self) -> list[dict[str, Any]]:
        """List all active operations"""
        return list(self.active_operations.values())

    def emergency_stop_all(self) -> None:
        """Emergency stop all operations (best effort)"""
        from .audit import audit_logger

        for operation_id in list(self.active_operations.keys()):
            operation = self.active_operations[operation_id]
            operation["status"] = "emergency_stopped"

            audit_logger.log_event(
                EventType.ERROR,
                Severity.CRITICAL,
                f"Emergency stop requested for operation: {operation['name']}",
                {"operation_id": operation_id},
            )

        self.active_operations.clear()


# Global secure operation manager
secure_ops = SecureOperationManager()


# Convenience functions
def secure_scan(
    directory: str, scan_function: Callable[[str], dict[str, Any]]
) -> OperationResult:
    """Securely scan a directory"""
    return secure_ops.secure_scan_directory(directory, scan_function)


def secure_delete(
    paths: list[str], operation_type: str = "Cache Cleanup"
) -> OperationResult:
    """Securely delete paths"""
    return secure_ops.secure_delete_paths(paths, operation_type)


def configure_security(
    enable_backups: bool = True, enable_confirmations: bool = True
) -> None:
    """Configure security settings"""
    global secure_ops
    secure_ops.enable_backups = enable_backups
    secure_ops.enable_confirmations = enable_confirmations


def get_operation_status(operation_id: str) -> Optional[dict[str, Any]]:
    """Get operation status"""
    return secure_ops.get_operation_status(operation_id)


def emergency_stop() -> None:
    """Emergency stop all operations"""
    secure_ops.emergency_stop_all()
