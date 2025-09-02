#!/usr/bin/env python3
"""
Recovery and Undo System for LazyScan

This module provides comprehensive recovery mechanisms including:
- Undo functionality for deletion operations
- Backup restoration capabilities
- Operation rollback with integrity verification
- Recovery history and status tracking

Author: Security Enhancement for LazyScan
Version: 1.0.0
"""

import os
import json
import shutil
import hashlib
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum

class RecoveryStatus(Enum):
    """Status of recovery operations"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"

class RecoveryType(Enum):
    """Type of recovery operation"""
    UNDO_DELETE = "undo_delete"
    RESTORE_BACKUP = "restore_backup"
    ROLLBACK_OPERATION = "rollback_operation"
    SELECTIVE_RESTORE = "selective_restore"

@dataclass
class RecoveryRecord:
    """Record of a recoverable operation"""
    operation_id: str
    operation_type: str
    timestamp: str
    original_paths: List[str]
    backup_paths: List[str]
    metadata: Dict[str, Any]
    files_affected: int
    size_affected: int
    checksum: str
    recovery_status: RecoveryStatus = RecoveryStatus.PENDING
    recovery_attempts: int = 0
    last_recovery_attempt: Optional[str] = None
    recovery_errors: List[str] = None

    def __post_init__(self):
        if self.recovery_errors is None:
            self.recovery_errors = []

@dataclass
class RecoveryResult:
    """Result of a recovery operation"""
    success: bool
    recovery_type: RecoveryType
    operation_id: str
    message: str
    restored_paths: List[str]
    failed_paths: List[str]
    files_restored: int
    size_restored: int
    duration: float
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []

class RecoveryManager:
    """
    Manages recovery operations and undo functionality for LazyScan.
    """

    def __init__(self, recovery_dir: str = None):
        # Set up recovery directory
        if recovery_dir is None:
            home_dir = Path.home()
            self.recovery_dir = home_dir / ".lazyscan" / "recovery"
        else:
            self.recovery_dir = Path(recovery_dir)

        self.recovery_dir.mkdir(parents=True, exist_ok=True)

        # Recovery database file
        self.recovery_db_file = self.recovery_dir / "recovery_records.json"

        # Load existing recovery records
        self.recovery_records: Dict[str, RecoveryRecord] = self._load_recovery_records()

        # Maximum age for recovery records (30 days)
        self.max_recovery_age = timedelta(days=30)

        # Clean up old records on initialization
        self._cleanup_old_records()

    def _load_recovery_records(self) -> Dict[str, RecoveryRecord]:
        """Load recovery records from disk"""
        if not self.recovery_db_file.exists():
            return {}

        try:
            with open(self.recovery_db_file, 'r') as f:
                data = json.load(f)

            records = {}
            for record_id, record_data in data.items():
                # Convert dict back to RecoveryRecord
                record_data['recovery_status'] = RecoveryStatus(record_data['recovery_status'])
                records[record_id] = RecoveryRecord(**record_data)

            return records

        except Exception as e:
            print(f"Warning: Could not load recovery records: {e}")
            return {}

    def _save_recovery_records(self) -> bool:
        """Save recovery records to disk"""
        try:
            # Convert RecoveryRecord objects to dicts
            data = {}
            for record_id, record in self.recovery_records.items():
                record_dict = asdict(record)
                record_dict['recovery_status'] = record.recovery_status.value
                data[record_id] = record_dict

            with open(self.recovery_db_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)

            return True

        except Exception as e:
            print(f"Error saving recovery records: {e}")
            return False

    def _calculate_checksum(self, data: str) -> str:
        """Calculate checksum for data integrity"""
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def _cleanup_old_records(self) -> None:
        """Clean up old recovery records"""
        current_time = datetime.now()
        expired_records = []

        for record_id, record in self.recovery_records.items():
            record_time = datetime.fromisoformat(record.timestamp)
            if current_time - record_time > self.max_recovery_age:
                expired_records.append(record_id)

        for record_id in expired_records:
            self._remove_recovery_record(record_id)

        if expired_records:
            print(f"Cleaned up {len(expired_records)} expired recovery records")

    def register_operation(self, operation_id: str, operation_type: str,
                         original_paths: List[str], backup_paths: List[str],
                         files_affected: int, size_affected: int,
                         metadata: Dict[str, Any] = None) -> bool:
        """
        Register an operation for potential recovery.

        Args:
            operation_id: Unique identifier for the operation
            operation_type: Type of operation (e.g., "Cache Cleanup")
            original_paths: Paths that were affected
            backup_paths: Paths where backups were created
            files_affected: Number of files affected
            size_affected: Total size affected in bytes
            metadata: Additional metadata

        Returns:
            bool: True if registration successful
        """
        if metadata is None:
            metadata = {}

        # Create checksum for integrity
        checksum_data = f"{operation_id}{operation_type}{','.join(original_paths)}{','.join(backup_paths)}"
        checksum = self._calculate_checksum(checksum_data)

        # Create recovery record
        record = RecoveryRecord(
            operation_id=operation_id,
            operation_type=operation_type,
            timestamp=datetime.now().isoformat(),
            original_paths=original_paths,
            backup_paths=backup_paths,
            metadata=metadata,
            files_affected=files_affected,
            size_affected=size_affected,
            checksum=checksum
        )

        # Store record
        self.recovery_records[operation_id] = record

        # Save to disk
        success = self._save_recovery_records()

        if success:
            from .audit import audit_logger, EventType, Severity
            audit_logger.log_event(
                EventType.BACKUP_CREATE,
                Severity.INFO,
                f"Recovery record created for operation: {operation_type}",
                {
                    "operation_id": operation_id,
                    "files_affected": files_affected,
                    "size_affected": size_affected,
                    "backup_count": len(backup_paths)
                }
            )

        return success

    def can_recover(self, operation_id: str) -> Tuple[bool, str]:
        """
        Check if an operation can be recovered.

        Args:
            operation_id: Operation to check

        Returns:
            Tuple[bool, str]: (can_recover, reason)
        """
        if operation_id not in self.recovery_records:
            return False, "Operation not found in recovery records"

        record = self.recovery_records[operation_id]

        # Check if backups still exist
        missing_backups = []
        for backup_path in record.backup_paths:
            if not os.path.exists(backup_path):
                missing_backups.append(backup_path)

        if missing_backups:
            return False, f"Missing backup files: {', '.join(missing_backups[:3])}"

        # Check if original paths are clear (not recreated)
        existing_originals = []
        for original_path in record.original_paths:
            if os.path.exists(original_path):
                existing_originals.append(original_path)

        if existing_originals:
            return False, f"Original paths already exist: {', '.join(existing_originals[:3])}"

        return True, "Recovery possible"

    def undo_operation(self, operation_id: str,
                      selective_paths: List[str] = None) -> RecoveryResult:
        """
        Undo a deletion operation by restoring from backups.

        Args:
            operation_id: Operation to undo
            selective_paths: Optional list of specific paths to restore

        Returns:
            RecoveryResult: Result of the recovery operation
        """
        start_time = time.time()

        # Check if recovery is possible
        can_recover, reason = self.can_recover(operation_id)
        if not can_recover:
            return RecoveryResult(
                success=False,
                recovery_type=RecoveryType.UNDO_DELETE,
                operation_id=operation_id,
                message=f"Cannot recover: {reason}",
                restored_paths=[],
                failed_paths=[],
                files_restored=0,
                size_restored=0,
                duration=time.time() - start_time
            )

        record = self.recovery_records[operation_id]
        record.recovery_attempts += 1
        record.last_recovery_attempt = datetime.now().isoformat()
        record.recovery_status = RecoveryStatus.IN_PROGRESS

        restored_paths = []
        failed_paths = []
        files_restored = 0
        size_restored = 0
        warnings = []

        try:
            # Determine which paths to restore
            if selective_paths:
                # Filter backup paths based on selective restore
                paths_to_restore = []
                for i, original_path in enumerate(record.original_paths):
                    if any(original_path.startswith(sel_path) or sel_path.startswith(original_path)
                          for sel_path in selective_paths):
                        if i < len(record.backup_paths):
                            paths_to_restore.append((original_path, record.backup_paths[i]))
            else:
                # Restore all paths
                paths_to_restore = list(zip(record.original_paths, record.backup_paths))

            # Perform restoration
            for original_path, backup_path in paths_to_restore:
                try:
                    if not os.path.exists(backup_path):
                        failed_paths.append(original_path)
                        record.recovery_errors.append(f"Backup not found: {backup_path}")
                        continue

                    # Create parent directories if needed
                    parent_dir = os.path.dirname(original_path)
                    if parent_dir and not os.path.exists(parent_dir):
                        os.makedirs(parent_dir, exist_ok=True)

                    # Restore file or directory
                    if os.path.isfile(backup_path):
                        shutil.copy2(backup_path, original_path)
                        size_restored += os.path.getsize(original_path)
                        files_restored += 1
                    elif os.path.isdir(backup_path):
                        shutil.copytree(backup_path, original_path)
                        # Count restored files and size
                        for root, dirs, files in os.walk(original_path):
                            for file in files:
                                try:
                                    file_path = os.path.join(root, file)
                                    size_restored += os.path.getsize(file_path)
                                    files_restored += 1
                                except (OSError, IOError):
                                    continue

                    restored_paths.append(original_path)

                except Exception as e:
                    failed_paths.append(original_path)
                    error_msg = f"Failed to restore {original_path}: {str(e)}"
                    record.recovery_errors.append(error_msg)
                    warnings.append(error_msg)

            # Update recovery status
            if failed_paths:
                record.recovery_status = RecoveryStatus.PARTIAL if restored_paths else RecoveryStatus.FAILED
            else:
                record.recovery_status = RecoveryStatus.COMPLETED

            duration = time.time() - start_time
            success = len(restored_paths) > 0

            # Log recovery operation
            from .audit import audit_logger, EventType, Severity
            audit_logger.log_event(
                EventType.BACKUP_RESTORE,
                Severity.INFO if success else Severity.ERROR,
                f"Recovery operation {'completed' if success else 'failed'}: {record.operation_type}",
                {
                    "operation_id": operation_id,
                    "files_restored": files_restored,
                    "size_restored": size_restored,
                    "failed_paths": len(failed_paths),
                    "duration": duration
                }
            )

            # Save updated record
            self._save_recovery_records()

            message = "Recovery completed successfully"
            if failed_paths:
                message = f"Recovery partially completed. {len(failed_paths)} paths failed."
            if not restored_paths:
                message = "Recovery failed. No paths were restored."

            return RecoveryResult(
                success=success,
                recovery_type=RecoveryType.UNDO_DELETE,
                operation_id=operation_id,
                message=message,
                restored_paths=restored_paths,
                failed_paths=failed_paths,
                files_restored=files_restored,
                size_restored=size_restored,
                duration=duration,
                warnings=warnings
            )

        except Exception as e:
            # Critical error during recovery
            record.recovery_status = RecoveryStatus.FAILED
            record.recovery_errors.append(f"Critical recovery error: {str(e)}")
            self._save_recovery_records()

            return RecoveryResult(
                success=False,
                recovery_type=RecoveryType.UNDO_DELETE,
                operation_id=operation_id,
                message=f"Critical recovery error: {str(e)}",
                restored_paths=restored_paths,
                failed_paths=failed_paths,
                files_restored=files_restored,
                size_restored=size_restored,
                duration=time.time() - start_time,
                warnings=[str(e)]
            )

    def list_recoverable_operations(self, days_back: int = 7) -> List[Dict[str, Any]]:
        """
        List operations that can be recovered.

        Args:
            days_back: Number of days to look back

        Returns:
            List of recoverable operations with details
        """
        cutoff_time = datetime.now() - timedelta(days=days_back)
        recoverable_ops = []

        for operation_id, record in self.recovery_records.items():
            record_time = datetime.fromisoformat(record.timestamp)
            if record_time < cutoff_time:
                continue

            can_recover, reason = self.can_recover(operation_id)

            op_info = {
                'operation_id': operation_id,
                'operation_type': record.operation_type,
                'timestamp': record.timestamp,
                'files_affected': record.files_affected,
                'size_affected': record.size_affected,
                'can_recover': can_recover,
                'recovery_status': record.recovery_status.value,
                'recovery_attempts': record.recovery_attempts,
                'reason': reason if not can_recover else 'Ready for recovery'
            }

            recoverable_ops.append(op_info)

        # Sort by timestamp (newest first)
        recoverable_ops.sort(key=lambda x: x['timestamp'], reverse=True)

        return recoverable_ops

    def get_recovery_statistics(self) -> Dict[str, Any]:
        """
        Get recovery system statistics.

        Returns:
            Dictionary with recovery statistics
        """
        total_records = len(self.recovery_records)
        recoverable_count = 0
        total_size_recoverable = 0
        total_files_recoverable = 0

        status_counts = {status.value: 0 for status in RecoveryStatus}

        for record in self.recovery_records.values():
            status_counts[record.recovery_status.value] += 1

            can_recover, _ = self.can_recover(record.operation_id)
            if can_recover:
                recoverable_count += 1
                total_size_recoverable += record.size_affected
                total_files_recoverable += record.files_affected

        return {
            'total_records': total_records,
            'recoverable_operations': recoverable_count,
            'total_size_recoverable': total_size_recoverable,
            'total_files_recoverable': total_files_recoverable,
            'status_breakdown': status_counts,
            'recovery_directory': str(self.recovery_dir),
            'database_size': os.path.getsize(self.recovery_db_file) if self.recovery_db_file.exists() else 0
        }

    def _remove_recovery_record(self, operation_id: str) -> bool:
        """
        Remove a recovery record and clean up associated backups.

        Args:
            operation_id: Operation to remove

        Returns:
            bool: True if removal successful
        """
        if operation_id not in self.recovery_records:
            return False

        record = self.recovery_records[operation_id]

        # Clean up backup files
        for backup_path in record.backup_paths:
            try:
                if os.path.exists(backup_path):
                    if os.path.isfile(backup_path):
                        os.remove(backup_path)
                    elif os.path.isdir(backup_path):
                        shutil.rmtree(backup_path)
            except Exception as e:
                print(f"Warning: Could not clean up backup {backup_path}: {e}")

        # Remove record
        del self.recovery_records[operation_id]

        # Save updated records
        return self._save_recovery_records()

    def cleanup_completed_recoveries(self, older_than_days: int = 7) -> int:
        """
        Clean up completed recovery records older than specified days.

        Args:
            older_than_days: Remove completed recoveries older than this

        Returns:
            int: Number of records cleaned up
        """
        cutoff_time = datetime.now() - timedelta(days=older_than_days)
        records_to_remove = []

        for operation_id, record in self.recovery_records.items():
            if record.recovery_status == RecoveryStatus.COMPLETED:
                record_time = datetime.fromisoformat(record.timestamp)
                if record_time < cutoff_time:
                    records_to_remove.append(operation_id)

        for operation_id in records_to_remove:
            self._remove_recovery_record(operation_id)

        return len(records_to_remove)

# Global recovery manager
recovery_manager = RecoveryManager()

# Convenience functions
def register_operation_for_recovery(operation_id: str, operation_type: str,
                                  original_paths: List[str], backup_paths: List[str],
                                  files_affected: int, size_affected: int,
                                  metadata: Dict[str, Any] = None) -> bool:
    """Register an operation for potential recovery"""
    return recovery_manager.register_operation(
        operation_id, operation_type, original_paths, backup_paths,
        files_affected, size_affected, metadata
    )

def undo_last_operation() -> Optional[RecoveryResult]:
    """Undo the most recent operation"""
    recent_ops = recovery_manager.list_recoverable_operations(days_back=1)
    if not recent_ops:
        return None

    # Find the most recent recoverable operation
    for op in recent_ops:
        if op['can_recover']:
            return recovery_manager.undo_operation(op['operation_id'])

    return None

def list_recent_operations(days_back: int = 7) -> List[Dict[str, Any]]:
    """List recent recoverable operations"""
    return recovery_manager.list_recoverable_operations(days_back)

def get_recovery_stats() -> Dict[str, Any]:
    """Get recovery system statistics"""
    return recovery_manager.get_recovery_statistics()

def cleanup_old_recoveries(older_than_days: int = 7) -> int:
    """Clean up old completed recovery records"""
    return recovery_manager.cleanup_completed_recoveries(older_than_days)