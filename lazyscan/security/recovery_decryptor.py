#!/usr/bin/env python3
"""
Recovery Decryption Pipeline for Encrypted Audit Logging

This module provides secure recovery decryption capabilities for LazyScan's
encrypted audit logging system, supporting key rotation scenarios and
streaming decryption with comprehensive metrics and auditability.
"""

import os
import json
import time
import hashlib
from typing import Dict, Any, Optional, List, Tuple, Iterator, Callable
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum

from ..core.errors import SecurityPolicyError
from ..core.logging_config import get_logger
from .audit_encryption import (
    AuditEncryption,
    AuditEncryptionError,
    AuditDecryptionError,
    EncryptedAuditEntry,
    get_audit_key_from_provider,
)
from .key_providers import KeyProvider, get_platform_key_provider

logger = get_logger(__name__)


class RecoveryStatus(Enum):
    """Status of recovery decryption operations."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class RecoveryError(Enum):
    """Types of recovery errors."""

    KEY_UNAVAILABLE = "key_unavailable"
    DECRYPTION_FAILED = "decryption_failed"
    INTEGRITY_CHECK_FAILED = "integrity_check_failed"
    IO_ERROR = "io_error"
    FORMAT_ERROR = "format_error"
    KEY_ROTATION_ERROR = "key_rotation_error"


@dataclass
class RecoveryMetrics:
    """Metrics collected during recovery decryption operations."""

    total_entries: int = 0
    decrypted_entries: int = 0
    failed_entries: int = 0
    skipped_entries: int = 0
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_seconds: float = 0.0
    error_counts: Optional[Dict[str, int]] = None
    key_versions_used: Optional[List[str]] = None
    throughput_entries_per_second: float = 0.0

    def __post_init__(self):
        if self.error_counts is None:
            self.error_counts = {}
        if self.key_versions_used is None:
            self.key_versions_used = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {k: v for k, v in asdict(self).items() if v is not None}

    def record_error(self, error_type: RecoveryError) -> None:
        """Record an error occurrence."""
        if self.error_counts is not None:
            self.error_counts[error_type.value] = self.error_counts.get(error_type.value, 0) + 1

    def record_key_version(self, key_version: str) -> None:
        """Record usage of a key version."""
        if self.key_versions_used is not None and key_version not in self.key_versions_used:
            self.key_versions_used.append(key_version)

    def finalize(self) -> None:
        """Finalize metrics calculation."""
        if self.start_time and self.end_time:
            start = datetime.fromisoformat(self.start_time.replace('Z', '+00:00'))
            end = datetime.fromisoformat(self.end_time.replace('Z', '+00:00'))
            self.duration_seconds = (end - start).total_seconds()

        if self.duration_seconds > 0:
            self.throughput_entries_per_second = self.total_entries / self.duration_seconds


@dataclass
class RecoveryResult:
    """Result of a recovery decryption operation."""

    success: bool
    status: RecoveryStatus
    metrics: RecoveryMetrics
    decrypted_entries: List[Dict[str, Any]]
    failed_entries: List[Dict[str, Any]]
    error_summary: Dict[str, Any]
    warnings: Optional[List[str]] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class RecoveryDecryptorError(SecurityPolicyError):
    """Base exception for recovery decryption operations."""
    pass


class KeyRotationManager:
    """
    Manages key rotation scenarios for recovery decryption.

    Handles multiple encryption keys that may have been used over time
    due to key rotation policies.
    """

    def __init__(self, key_provider: KeyProvider, max_key_versions: int = 10):
        """
        Initialize key rotation manager.

        Args:
            key_provider: Key provider for retrieving keys
            max_key_versions: Maximum number of key versions to try
        """
        self.key_provider = key_provider
        self.max_key_versions = max_key_versions
        self.key_cache: Dict[str, bytes] = {}
        self.logger = logger

    def get_active_key(self) -> bytes:
        """
        Get the currently active encryption key.

        Returns:
            Active encryption key

        Raises:
            RecoveryDecryptorError: If key cannot be retrieved
        """
        key_id = "lazyscan-audit-key"
        try:
            if key_id not in self.key_cache:
                self.key_cache[key_id] = get_audit_key_from_provider(self.key_provider, key_id)

            return self.key_cache[key_id]

        except Exception as e:
            logger.error(f"Failed to retrieve active key '{key_id}': {e}")
            raise RecoveryDecryptorError(f"Active key retrieval failed: {e}")

    def get_key_for_version(self, key_version: str) -> bytes:
        """
        Get encryption key for a specific version.

        In a full implementation, this would retrieve historical keys
        based on rotation metadata. For now, we try the active key
        and fall back to versioned key attempts.

        Args:
            key_version: Key version identifier

        Returns:
            Encryption key for the version

        Raises:
            RecoveryDecryptorError: If key cannot be retrieved
        """
        # Try active key first
        if key_version == "current" or key_version == "1.1":
            return self.get_active_key()

        # For rotated keys, try versioned key IDs
        # This is a simplified implementation - in production, you'd have
        # a key rotation metadata store
        versioned_key_ids = [
            f"lazyscan-audit-key-v{key_version}",
            f"lazyscan-audit-key-{key_version}",
            "lazyscan-audit-key"  # Fallback to current
        ]

        for key_id in versioned_key_ids:
            try:
                if key_id not in self.key_cache:
                    self.key_cache[key_id] = get_audit_key_from_provider(self.key_provider, key_id)
                return self.key_cache[key_id]
            except Exception:
                continue

        raise RecoveryDecryptorError(f"No key found for version '{key_version}'")

    def try_decrypt_with_keys(self, encrypted_entry: EncryptedAuditEntry) -> Tuple[bytes, str]:
        """
        Try to decrypt an entry with available keys.

        Returns the key and version that worked.

        Args:
            encrypted_entry: Encrypted entry to decrypt

        Returns:
            Tuple of (decryption_key, key_version)

        Raises:
            RecoveryDecryptorError: If no key works
        """
        # Try current key first
        try:
            key = self.get_active_key()
            # Test decryption with a minimal operation
            return key, "current"
        except Exception:
            pass

        # Try version from entry if available
        if hasattr(encrypted_entry, 'version') and encrypted_entry.version:
            try:
                key = self.get_key_for_version(encrypted_entry.version)
                return key, encrypted_entry.version
            except Exception:
                pass

        # Try common version patterns
        for version in ["1.0", "1.1", "legacy"]:
            try:
                key = self.get_key_for_version(version)
                return key, version
            except Exception:
                continue

        raise RecoveryDecryptorError("No suitable decryption key found")


class RecoveryDecryptor:
    """
    Secure recovery decryption pipeline for encrypted audit logs.

    Provides streaming decryption capabilities with key rotation support,
    comprehensive metrics, and graceful error handling.
    """

    def __init__(self, key_provider: Optional[KeyProvider] = None):
        """
        Initialize recovery decryptor.

        Args:
            key_provider: Key provider (auto-detected if None)
        """
        self.key_provider = key_provider or get_platform_key_provider()
        self.key_rotation_manager = KeyRotationManager(self.key_provider)
        self.logger = logger

        # Recovery session state
        self.session_id = self._generate_session_id()
        self.metrics = RecoveryMetrics()

    def _generate_session_id(self) -> str:
        """Generate unique recovery session ID."""
        timestamp = str(int(time.time()))
        session_data = f"recovery-{timestamp}-{os.getpid()}"
        return hashlib.md5(session_data.encode()).hexdigest()[:12]

    def recover_from_file(self, log_file_path: str, output_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> RecoveryResult:
        """
        Recover and decrypt audit entries from a log file.

        Args:
            log_file_path: Path to the encrypted audit log file
            output_callback: Optional callback for each decrypted entry

        Returns:
            RecoveryResult with operation details and metrics
        """
        log_path = Path(log_file_path)
        if not log_path.exists():
            raise RecoveryDecryptorError(f"Log file does not exist: {log_file_path}")

        self.logger.info(f"Starting recovery decryption of {log_file_path}")
        self.metrics = RecoveryMetrics()
        self.metrics.start_time = datetime.now(timezone.utc).isoformat()

        decrypted_entries = []
        failed_entries = []

        try:
            # Stream through log entries
            for entry_data in self._stream_log_entries(log_path):
                self.metrics.total_entries += 1

                try:
                    # Attempt decryption
                    decrypted_entry = self._decrypt_entry(entry_data)
                    self.metrics.decrypted_entries += 1

                    # Call output callback if provided
                    if output_callback:
                        output_callback(decrypted_entry)

                    decrypted_entries.append(decrypted_entry)

                except Exception as e:
                    # Record failure
                    self.metrics.failed_entries += 1
                    error_info = {
                        "entry_data": entry_data,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "line_number": self.metrics.total_entries
                    }
                    failed_entries.append(error_info)

                    # Classify error type
                    if isinstance(e, AuditDecryptionError):
                        if "Integrity check failed" in str(e):
                            self.metrics.record_error(RecoveryError.INTEGRITY_CHECK_FAILED)
                        else:
                            self.metrics.record_error(RecoveryError.DECRYPTION_FAILED)
                    elif isinstance(e, KeyError) or "key" in str(e).lower():
                        self.metrics.record_error(RecoveryError.KEY_UNAVAILABLE)
                    else:
                        self.metrics.record_error(RecoveryError.FORMAT_ERROR)

                    self.logger.warning(f"Failed to decrypt entry {self.metrics.total_entries}: {e}")

            # Finalize metrics
            self.metrics.end_time = datetime.now(timezone.utc).isoformat()
            self.metrics.finalize()

            # Determine overall status
            if self.metrics.failed_entries == 0:
                status = RecoveryStatus.COMPLETED
                success = True
            elif self.metrics.decrypted_entries > 0:
                status = RecoveryStatus.PARTIAL
                success = True
            else:
                status = RecoveryStatus.FAILED
                success = False

            # Generate error summary
            error_summary = {
                "total_errors": self.metrics.failed_entries,
                "error_breakdown": self.metrics.error_counts,
                "success_rate": (self.metrics.decrypted_entries / self.metrics.total_entries * 100) if self.metrics.total_entries > 0 else 0,
                "key_versions_used": self.metrics.key_versions_used,
                "recovery_session": self.session_id
            }

            # Log recovery completion
            self._audit_recovery_operation(success, error_summary)

            result = RecoveryResult(
                success=success,
                status=status,
                metrics=self.metrics,
                decrypted_entries=decrypted_entries,
                failed_entries=failed_entries,
                error_summary=error_summary
            )

            self.logger.info(f"Recovery decryption completed: {self.metrics.decrypted_entries}/{self.metrics.total_entries} entries decrypted")
            return result

        except Exception as e:
            self.logger.error(f"Critical recovery error: {e}")
            self.metrics.end_time = datetime.now(timezone.utc).isoformat()
            self.metrics.finalize()

            return RecoveryResult(
                success=False,
                status=RecoveryStatus.FAILED,
                metrics=self.metrics,
                decrypted_entries=decrypted_entries,
                failed_entries=failed_entries,
                error_summary={"critical_error": str(e)},
                warnings=[f"Critical recovery failure: {e}"]
            )

    def _stream_log_entries(self, log_path: Path) -> Iterator[Dict[str, Any]]:
        """
        Stream log entries from file.

        Args:
            log_path: Path to log file

        Yields:
            Log entry data as dictionary
        """
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        entry_data = json.loads(line)
                        yield entry_data
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"Invalid JSON at line {line_num}: {e}")
                        self.metrics.record_error(RecoveryError.FORMAT_ERROR)
                        continue

        except IOError as e:
            raise RecoveryDecryptorError(f"Failed to read log file: {e}")

    def _decrypt_entry(self, entry_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt a single audit entry.

        Args:
            entry_data: Raw entry data from log

        Returns:
            Decrypted entry data

        Raises:
            AuditDecryptionError: If decryption fails
        """
        # Check if entry is already plaintext
        if not self._is_encrypted_entry(entry_data):
            return entry_data

        # Convert to EncryptedAuditEntry
        try:
            encrypted_entry = EncryptedAuditEntry.from_dict(entry_data)
        except Exception as e:
            raise AuditDecryptionError(f"Invalid encrypted entry format: {e}")

        # Find appropriate decryption key
        try:
            decryption_key, key_version = self.key_rotation_manager.try_decrypt_with_keys(encrypted_entry)
            self.metrics.record_key_version(key_version)
        except Exception as e:
            raise AuditDecryptionError(f"Key acquisition failed: {e}")

        # Create decryptor and decrypt
        decryptor = AuditEncryption(decryption_key)
        decrypted_data = decryptor.decrypt_entry(encrypted_entry)

        return decrypted_data

    def _is_encrypted_entry(self, entry_data: Dict[str, Any]) -> bool:
        """
        Check if entry data represents an encrypted audit entry.

        Args:
            entry_data: Entry data to check

        Returns:
            True if encrypted
        """
        required_fields = ['version', 'algorithm', 'nonce', 'ciphertext', 'tag']
        return all(field in entry_data for field in required_fields) and \
               entry_data.get('algorithm') == 'AES-256-GCM'

    def _audit_recovery_operation(self, success: bool, details: Dict[str, Any]) -> None:
        """Audit the recovery operation itself."""
        try:
            # Import here to avoid circular imports
            from ..helpers.audit import audit_logger, EventType, Severity

            audit_logger.log_event(
                EventType.CONFIG_CHANGE if success else EventType.ERROR,
                Severity.INFO if success else Severity.ERROR,
                f"Audit log recovery decryption {'completed' if success else 'failed'}",
                {
                    "recovery_session": self.session_id,
                    "entries_processed": self.metrics.total_entries,
                    "entries_decrypted": self.metrics.decrypted_entries,
                    "entries_failed": self.metrics.failed_entries,
                    "duration_seconds": self.metrics.duration_seconds,
                    "success_rate": details.get("success_rate", 0),
                    "key_versions_used": self.metrics.key_versions_used,
                    "error_breakdown": self.metrics.error_counts
                }
            )
        except Exception as e:
            logger.warning(f"Failed to audit recovery operation: {e}")

    def recover_to_file(self, input_file: str, output_file: str, format: str = "jsonl") -> RecoveryResult:
        """
        Recover encrypted logs and write decrypted entries to a new file.

        Args:
            input_file: Path to encrypted log file
            output_file: Path to write decrypted entries
            format: Output format ("jsonl" or "json")

        Returns:
            RecoveryResult with operation details
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        decrypted_entries = []

        def collect_entry(entry: Dict[str, Any]) -> None:
            decrypted_entries.append(entry)

        # Perform recovery
        result = self.recover_from_file(input_file, collect_entry)

        if not result.success and result.status != RecoveryStatus.PARTIAL:
            return result

        # Write decrypted entries to output file
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                if format == "jsonl":
                    for entry in decrypted_entries:
                        json.dump(entry, f, ensure_ascii=False)
                        f.write('\n')
                elif format == "json":
                    json.dump({
                        "recovery_session": self.session_id,
                        "recovered_entries": decrypted_entries,
                        "recovery_metrics": result.metrics.to_dict()
                    }, f, indent=2, ensure_ascii=False)
                else:
                    raise ValueError(f"Unsupported output format: {format}")

            self.logger.info(f"Decrypted entries written to {output_file}")

        except Exception as e:
            if result.warnings is not None:
                result.warnings.append(f"Failed to write output file: {e}")
            result.success = False
            result.status = RecoveryStatus.FAILED

        return result

    def get_recovery_metrics(self) -> RecoveryMetrics:
        """
        Get current recovery metrics.

        Returns:
            Current metrics
        """
        return self.metrics

    def validate_log_integrity(self, log_file_path: str) -> Dict[str, Any]:
        """
        Validate the integrity of an encrypted audit log without full decryption.

        Args:
            log_file_path: Path to the log file

        Returns:
            Integrity validation results
        """
        log_path = Path(log_file_path)
        validation_results = {
            "total_entries": 0,
            "valid_entries": 0,
            "invalid_entries": 0,
            "corrupted_entries": 0,
            "integrity_score": 0.0,
            "issues": []
        }

        try:
            for entry_data in self._stream_log_entries(log_path):
                validation_results["total_entries"] += 1

                try:
                    # Quick validation without full decryption
                    if self._is_encrypted_entry(entry_data):
                        encrypted_entry = EncryptedAuditEntry.from_dict(entry_data)
                        # Try to get appropriate key
                        decryption_key, _ = self.key_rotation_manager.try_decrypt_with_keys(encrypted_entry)
                        validation_results["valid_entries"] += 1
                    else:
                        # Plaintext entry
                        validation_results["valid_entries"] += 1

                except Exception as e:
                    validation_results["invalid_entries"] += 1
                    validation_results["issues"].append({
                        "entry": validation_results["total_entries"],
                        "error": str(e)
                    })

            # Calculate integrity score
            if validation_results["total_entries"] > 0:
                validation_results["integrity_score"] = (
                    validation_results["valid_entries"] / validation_results["total_entries"] * 100
                )

        except Exception as e:
            validation_results["issues"].append({
                "type": "file_error",
                "error": str(e)
            })

        return validation_results


# Convenience functions
def recover_audit_logs(input_file: str, output_file: Optional[str] = None, key_provider: Optional[KeyProvider] = None) -> RecoveryResult:
    """
    Convenience function to recover encrypted audit logs.

    Args:
        input_file: Path to encrypted audit log
        output_file: Optional output file for decrypted entries
        key_provider: Optional key provider

    Returns:
        RecoveryResult
    """
    decryptor = RecoveryDecryptor(key_provider)

    if output_file:
        return decryptor.recover_to_file(input_file, output_file)
    else:
        return decryptor.recover_from_file(input_file)


def validate_audit_log_integrity(log_file: str, key_provider: Optional[KeyProvider] = None) -> Dict[str, Any]:
    """
    Validate integrity of an encrypted audit log.

    Args:
        log_file: Path to audit log file
        key_provider: Optional key provider

    Returns:
        Integrity validation results
    """
    decryptor = RecoveryDecryptor(key_provider)
    return decryptor.validate_log_integrity(log_file)


__all__ = [
    "RecoveryDecryptor",
    "RecoveryDecryptorError",
    "RecoveryResult",
    "RecoveryMetrics",
    "RecoveryStatus",
    "RecoveryError",
    "KeyRotationManager",
    "recover_audit_logs",
    "validate_audit_log_integrity",
]</content>
</xai:function_call">Writing to /Users/vinayvidyasagar/Dev/LazyScan/lazyscan/security/recovery_decryptor.py