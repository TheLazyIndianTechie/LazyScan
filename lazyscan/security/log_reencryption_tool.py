#!/usr/bin/env python3
"""
Log Re-encryption Tool for Key Rotation

This module provides streaming re-encryption tooling for LazyScan's audit logs
during key rotation scenarios. It decrypts logs with retiring keys and re-encrypts
them with active keys in chunked batches, with atomic finalization and resumable
checkpoints for interrupted operations.
"""

import os
import json
import hashlib
import tempfile
import shutil
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Iterator, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum

from ..core.errors import SecurityPolicyError
from ..core.logging_config import get_logger
from .audit_encryption import (
    AuditEncryption,
    AuditEncryptionError,
    EncryptedAuditEntry,
    get_audit_key_from_provider,
)
from .key_providers import KeyProvider, get_platform_key_provider

logger = get_logger(__name__)


class ReencryptionStatus(Enum):
    """Status of re-encryption operations."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class ReencryptionPhase(Enum):
    """Re-encryption processing phases."""

    INITIALIZATION = "initialization"
    KEY_VALIDATION = "key_validation"
    BATCH_PROCESSING = "batch_processing"
    INTEGRITY_VERIFICATION = "integrity_verification"
    ATOMIC_SWAP = "atomic_swap"
    CLEANUP = "cleanup"


@dataclass
class ReencryptionBatch:
    """Represents a batch of entries being re-encrypted."""

    batch_id: str
    start_entry: int
    end_entry: int
    entry_count: int
    integrity_hash: str
    status: str
    processed_at: Optional[str] = None
    verification_hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReencryptionBatch":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class ReencryptionCheckpoint:
    """Checkpoint for resumable re-encryption operations."""

    operation_id: str
    phase: str
    status: str
    source_file: str
    target_file: str
    retiring_key_id: str
    active_key_id: str
    total_entries: int
    processed_entries: int
    batches: List[ReencryptionBatch]
    start_time: str
    last_update: str
    integrity_proofs: Dict[str, str]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["batches"] = [batch.to_dict() for batch in self.batches]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReencryptionCheckpoint":
        """Create from dictionary."""
        batches_data = data.pop("batches", [])
        batches = [ReencryptionBatch.from_dict(b) for b in batches_data]
        return cls(batches=batches, **data)

    def add_batch(self, batch: ReencryptionBatch):
        """Add a processed batch to the checkpoint."""
        self.batches.append(batch)
        self.processed_entries += batch.entry_count
        self.last_update = datetime.now(timezone.utc).isoformat()

    def get_incomplete_batches(self) -> List[ReencryptionBatch]:
        """Get batches that haven't been completed yet."""
        return [b for b in self.batches if b.status != ReencryptionStatus.COMPLETED.value]


@dataclass
class ReencryptionResult:
    """Result of a re-encryption operation."""

    success: bool
    status: ReencryptionStatus
    operation_id: str
    total_entries: int
    processed_entries: int
    failed_entries: int
    batches_processed: int
    integrity_verified: bool
    duration_seconds: float
    error_summary: Dict[str, Any]
    warnings: Optional[List[str]] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class LogReencryptionTool:
    """
    Streaming re-encryption tool for audit logs during key rotation.

    This tool provides resumable, chunked re-encryption of encrypted audit logs
    when encryption keys are rotated, ensuring data integrity and atomic operations.
    """

    # Batch size for processing entries
    DEFAULT_BATCH_SIZE = 1000

    # Maximum batches to keep in memory
    MAX_BATCHES_IN_MEMORY = 10

    def __init__(self,
                 key_provider: Optional[KeyProvider] = None,
                 batch_size: int = DEFAULT_BATCH_SIZE):
        """
        Initialize the re-encryption tool.

        Args:
            key_provider: Key provider for retrieving encryption keys
            batch_size: Number of entries to process per batch
        """
        self.key_provider = key_provider or get_platform_key_provider()
        self.batch_size = batch_size
        self.operation_id = self._generate_operation_id()

        # Checkpoint management
        self.checkpoint_dir = self._get_checkpoint_dir()
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Initialized LogReencryptionTool",
                   operation_id=self.operation_id,
                   batch_size=batch_size)

    def _generate_operation_id(self) -> str:
        """Generate unique operation ID."""
        timestamp = str(int(time.time()))
        session_data = f"reencrypt-{timestamp}-{os.getpid()}"
        return hashlib.md5(session_data.encode()).hexdigest()[:12]

    def _get_checkpoint_dir(self) -> Path:
        """Get directory for storing checkpoints."""
        # Use platform-specific temp directory for checkpoints
        if os.name == "nt":  # Windows
            temp_dir = Path(os.environ.get("TEMP", "C:\\Temp"))
        else:  # Unix-like systems
            temp_dir = Path("/tmp")

        return temp_dir / "lazyscan_reencryption_checkpoints"

    def reencrypt_log_file(self,
                          source_file: str,
                          retiring_key_id: str,
                          active_key_id: str,
                          resume_from_checkpoint: Optional[str] = None) -> ReencryptionResult:
        """
        Re-encrypt an audit log file with new encryption key.

        Args:
            source_file: Path to the source encrypted log file
            retiring_key_id: ID of the retiring encryption key
            active_key_id: ID of the new active encryption key
            resume_from_checkpoint: Optional checkpoint ID to resume from

        Returns:
            ReencryptionResult with operation details
        """
        source_path = Path(source_file)
        if not source_path.exists():
            raise SecurityPolicyError(f"Source file does not exist: {source_file}")

        start_time = time.time()
        operation_id = resume_from_checkpoint or self.operation_id

        logger.info("Starting log re-encryption",
                   operation_id=operation_id,
                   source_file=source_file,
                   retiring_key_id=retiring_key_id,
                   active_key_id=active_key_id)

        try:
            # Load or create checkpoint
            if resume_from_checkpoint:
                checkpoint = self.load_checkpoint(resume_from_checkpoint)
                if not checkpoint:
                    raise SecurityPolicyError(f"Checkpoint not found: {resume_from_checkpoint}")
            else:
                checkpoint = self._create_initial_checkpoint(source_path, retiring_key_id, active_key_id)

            # Validate keys
            checkpoint.phase = ReencryptionPhase.KEY_VALIDATION.value
            self._save_checkpoint(checkpoint)

            retiring_key = self._get_key(retiring_key_id)
            active_key = self._get_key(active_key_id)

            # Count total entries if not resuming
            if checkpoint.total_entries == 0:
                checkpoint.total_entries = self._count_entries(source_path)
                self._save_checkpoint(checkpoint)

            # Create temporary target file
            target_file = self._create_temp_target_file(source_path)
            checkpoint.target_file = str(target_file)

            # Process in batches
            checkpoint.phase = ReencryptionPhase.BATCH_PROCESSING.value
            self._save_checkpoint(checkpoint)

            success = self._process_batches(checkpoint, source_path, target_file, retiring_key, active_key)

            if success:
                # Verify integrity
                checkpoint.phase = ReencryptionPhase.INTEGRITY_VERIFICATION.value
                self._save_checkpoint(checkpoint)

                integrity_ok = self._verify_integrity(checkpoint, target_file)
                if not integrity_ok:
                    raise SecurityPolicyError("Integrity verification failed")

                # Atomic swap
                checkpoint.phase = ReencryptionPhase.ATOMIC_SWAP.value
                self._save_checkpoint(checkpoint)

                self._perform_atomic_swap(source_path, target_file)

                # Cleanup
                checkpoint.phase = ReencryptionPhase.CLEANUP.value
                checkpoint.status = ReencryptionStatus.COMPLETED.value
                self._save_checkpoint(checkpoint)

                self._cleanup_temp_files(target_file)

            else:
                checkpoint.status = ReencryptionStatus.FAILED.value
                self._save_checkpoint(checkpoint)

            # Calculate final metrics
            duration = time.time() - start_time
            processed_entries = sum(b.entry_count for b in checkpoint.batches
                                  if b.status == ReencryptionStatus.COMPLETED.value)
            failed_entries = checkpoint.total_entries - processed_entries

            result = ReencryptionResult(
                success=success,
                status=ReencryptionStatus.COMPLETED if success else ReencryptionStatus.FAILED,
                operation_id=operation_id,
                total_entries=checkpoint.total_entries,
                processed_entries=processed_entries,
                failed_entries=failed_entries,
                batches_processed=len([b for b in checkpoint.batches
                                     if b.status == ReencryptionStatus.COMPLETED.value]),
                integrity_verified=success,
                duration_seconds=duration,
                error_summary=self._generate_error_summary(checkpoint)
            )

            self._audit_operation(result)
            return result

        except Exception as e:
            logger.error(f"Re-encryption failed: {e}")
            duration = time.time() - start_time

            # Try to save failed checkpoint
            try:
                if 'checkpoint' in locals():
                    checkpoint.status = ReencryptionStatus.FAILED.value
                    checkpoint.metadata["failure_reason"] = str(e)
                    self._save_checkpoint(checkpoint)
            except Exception:
                pass  # Ignore checkpoint save failures

            return ReencryptionResult(
                success=False,
                status=ReencryptionStatus.FAILED,
                operation_id=operation_id,
                total_entries=getattr(checkpoint, 'total_entries', 0) if 'checkpoint' in locals() else 0,
                processed_entries=0,
                failed_entries=getattr(checkpoint, 'total_entries', 0) if 'checkpoint' in locals() else 0,
                batches_processed=0,
                integrity_verified=False,
                duration_seconds=duration,
                error_summary={"critical_error": str(e)},
                warnings=[f"Critical failure: {e}"]
            )

    def _create_initial_checkpoint(self, source_path: Path, retiring_key_id: str, active_key_id: str) -> ReencryptionCheckpoint:
        """Create initial checkpoint for new operation."""
        return ReencryptionCheckpoint(
            operation_id=self.operation_id,
            phase=ReencryptionPhase.INITIALIZATION.value,
            status=ReencryptionStatus.IN_PROGRESS.value,
            source_file=str(source_path),
            target_file="",
            retiring_key_id=retiring_key_id,
            active_key_id=active_key_id,
            total_entries=0,
            processed_entries=0,
            batches=[],
            start_time=datetime.now(timezone.utc).isoformat(),
            last_update=datetime.now(timezone.utc).isoformat(),
            integrity_proofs={},
            metadata={
                "tool_version": "1.0",
                "batch_size": self.batch_size,
                "platform": os.name
            }
        )

    def _get_key(self, key_id: str) -> bytes:
        """Retrieve encryption key by ID."""
        try:
            return get_audit_key_from_provider(self.key_provider, key_id)
        except Exception as e:
            raise SecurityPolicyError(f"Failed to retrieve key '{key_id}': {e}")

    def _count_entries(self, source_path: Path) -> int:
        """Count total entries in the source file."""
        count = 0
        try:
            with open(source_path, 'r', encoding='utf-8') as f:
                for _ in f:
                    count += 1
        except Exception as e:
            logger.warning(f"Could not count entries: {e}")
            # Fallback: estimate based on file size (rough heuristic)
            file_size = source_path.stat().st_size
            count = max(1, file_size // 200)  # Assume ~200 bytes per entry
            logger.info(f"Estimated entry count: {count} (file size: {file_size})")

        return count

    def _create_temp_target_file(self, source_path: Path) -> Path:
        """Create temporary target file for re-encryption."""
        temp_dir = source_path.parent
        temp_name = f"{source_path.stem}_reencrypt_{self.operation_id}{source_path.suffix}"
        return temp_dir / temp_name

    def _process_batches(self, checkpoint: ReencryptionCheckpoint, source_path: Path,
                        target_file: Path, retiring_key: bytes, active_key: bytes) -> bool:
        """Process entries in batches."""
        try:
            batch_num = 0
            entry_offset = 0

            # Resume from incomplete batches if any
            incomplete_batches = checkpoint.get_incomplete_batches()
            if incomplete_batches:
                # Resume from first incomplete batch
                last_complete_batch = None
                for batch in checkpoint.batches:
                    if batch.status == ReencryptionStatus.COMPLETED.value:
                        last_complete_batch = batch
                    else:
                        break

                if last_complete_batch:
                    entry_offset = last_complete_batch.end_entry + 1
                    batch_num = len([b for b in checkpoint.batches
                                   if b.status == ReencryptionStatus.COMPLETED.value])

            with open(source_path, 'r', encoding='utf-8') as source_f:
                # Skip to resume point
                for _ in range(entry_offset):
                    next(source_f, None)

                with open(target_file, 'w', encoding='utf-8') as target_f:
                    batch_entries = []
                    batch_start = entry_offset

                    for line_num, line in enumerate(source_f, entry_offset):
                        line = line.strip()
                        if not line:
                            continue

                        batch_entries.append(line)

                        # Process batch when it reaches the target size
                        if len(batch_entries) >= self.batch_size:
                            success = self._process_batch(
                                batch_num, batch_entries, batch_start, line_num,
                                retiring_key, active_key, target_f, checkpoint
                            )

                            if not success:
                                return False

                            batch_num += 1
                            batch_entries = []
                            batch_start = line_num + 1

                    # Process final partial batch
                    if batch_entries:
                        success = self._process_batch(
                            batch_num, batch_entries, batch_start, line_num,
                            retiring_key, active_key, target_f, checkpoint
                        )

                        if not success:
                            return False

            return True

        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            return False

    def _process_batch(self, batch_num: int, entries: List[str], start_entry: int,
                      end_entry: int, retiring_key: bytes, active_key: bytes,
                      target_f, checkpoint: ReencryptionCheckpoint) -> bool:
        """Process a single batch of entries."""
        try:
            batch_id = f"batch_{batch_num:06d}"

            # Create batch record
            batch = ReencryptionBatch(
                batch_id=batch_id,
                start_entry=start_entry,
                end_entry=end_entry,
                entry_count=len(entries),
                integrity_hash=self._calculate_batch_hash(entries),
                status=ReencryptionStatus.IN_PROGRESS.value
            )

            logger.debug(f"Processing batch {batch_id}",
                        entries=len(entries),
                        range=f"{start_entry}-{end_entry}")

            # Re-encrypt entries
            reencrypted_entries = []
            decryptor = AuditEncryption(retiring_key)
            encryptor = AuditEncryption(active_key)

            for entry_line in entries:
                try:
                    # Parse entry
                    entry_data = json.loads(entry_line)

                    # Skip if not encrypted
                    if not self._is_encrypted_entry(entry_data):
                        reencrypted_entries.append(entry_line)
                        continue

                    # Decrypt with retiring key
                    encrypted_entry = EncryptedAuditEntry.from_dict(entry_data)
                    decrypted_data = decryptor.decrypt_entry(encrypted_entry)

                    # Re-encrypt with active key
                    reencrypted_entry = encryptor.encrypt_entry(decrypted_data)
                    reencrypted_line = json.dumps(reencrypted_entry.to_dict(), ensure_ascii=False)

                    reencrypted_entries.append(reencrypted_line)

                except Exception as e:
                    logger.warning(f"Failed to re-encrypt entry in batch {batch_id}: {e}")
                    # On failure, keep original entry
                    reencrypted_entries.append(entry_line)

            # Write batch to target file
            for entry_line in reencrypted_entries:
                target_f.write(entry_line + '\n')

            # Mark batch as completed
            batch.status = ReencryptionStatus.COMPLETED.value
            batch.processed_at = datetime.now(timezone.utc).isoformat()
            batch.verification_hash = self._calculate_batch_hash(reencrypted_entries)

            # Update checkpoint
            checkpoint.add_batch(batch)
            checkpoint.integrity_proofs[batch_id] = batch.verification_hash

            # Save checkpoint periodically
            if batch_num % 10 == 0:  # Every 10 batches
                self._save_checkpoint(checkpoint)

            logger.debug(f"Completed batch {batch_id}",
                        processed=len(reencrypted_entries),
                        integrity_hash=batch.verification_hash[:16])

            return True

        except Exception as e:
            logger.error(f"Batch {batch_num} processing failed: {e}")
            return False

    def _calculate_batch_hash(self, entries: List[str]) -> str:
        """Calculate integrity hash for a batch of entries."""
        hasher = hashlib.sha256()
        for entry in entries:
            hasher.update(entry.encode('utf-8'))
        return hasher.hexdigest()

    def _is_encrypted_entry(self, entry_data: Dict[str, Any]) -> bool:
        """Check if entry data represents an encrypted audit entry."""
        required_fields = ['version', 'algorithm', 'nonce', 'ciphertext', 'tag']
        return all(field in entry_data for field in required_fields) and \
               entry_data.get('algorithm') == 'AES-256-GCM'

    def _verify_integrity(self, checkpoint: ReencryptionCheckpoint, target_file: Path) -> bool:
        """Verify integrity of the re-encrypted file."""
        try:
            # Recalculate hashes for all batches
            current_offset = 0
            verified_batches = 0

            with open(target_file, 'r', encoding='utf-8') as f:
                for batch in checkpoint.batches:
                    if batch.status != ReencryptionStatus.COMPLETED.value:
                        continue

                    # Read batch entries
                    batch_entries = []
                    for _ in range(batch.entry_count):
                        line = f.readline().strip()
                        if not line:
                            break
                        batch_entries.append(line)

                    if len(batch_entries) != batch.entry_count:
                        logger.error(f"Batch {batch.batch_id} size mismatch: expected {batch.entry_count}, got {len(batch_entries)}")
                        return False

                    # Verify hash
                    current_hash = self._calculate_batch_hash(batch_entries)
                    if current_hash != batch.verification_hash:
                        logger.error(f"Batch {batch.batch_id} integrity check failed: {current_hash} != {batch.verification_hash}")
                        return False

                    verified_batches += 1

            logger.info(f"Integrity verification passed: {verified_batches}/{len(checkpoint.batches)} batches verified")
            return True

        except Exception as e:
            logger.error(f"Integrity verification failed: {e}")
            return False

    def _perform_atomic_swap(self, source_path: Path, target_file: Path):
        """Perform atomic file swap."""
        try:
            # Create backup of original
            backup_file = source_path.with_suffix(source_path.suffix + '.backup')
            shutil.copy2(source_path, backup_file)

            # Atomic rename
            target_file.replace(source_path)

            logger.info("Atomic swap completed",
                       source=str(source_path),
                       backup=str(backup_file))

        except Exception as e:
            logger.error(f"Atomic swap failed: {e}")
            raise SecurityPolicyError(f"Failed to perform atomic swap: {e}")

    def _cleanup_temp_files(self, target_file: Path):
        """Clean up temporary files."""
        try:
            if target_file.exists():
                target_file.unlink()
        except Exception as e:
            logger.warning(f"Failed to cleanup temp file {target_file}: {e}")

    def _generate_error_summary(self, checkpoint: ReencryptionCheckpoint) -> Dict[str, Any]:
        """Generate error summary from checkpoint."""
        failed_batches = [b for b in checkpoint.batches if b.status == ReencryptionStatus.FAILED.value]
        incomplete_batches = [b for b in checkpoint.batches if b.status == ReencryptionStatus.IN_PROGRESS.value]

        return {
            "failed_batches": len(failed_batches),
            "incomplete_batches": len(incomplete_batches),
            "total_batches": len(checkpoint.batches),
            "failure_reason": checkpoint.metadata.get("failure_reason"),
            "last_phase": checkpoint.phase
        }

    def _audit_operation(self, result: ReencryptionResult):
        """Audit the re-encryption operation."""
        try:
            # Import here to avoid circular imports
            from ..helpers.audit import audit_logger, EventType, Severity

            audit_logger.log_event(
                EventType.CONFIG_CHANGE if result.success else EventType.ERROR,
                Severity.INFO if result.success else Severity.ERROR,
                f"Audit log re-encryption {'completed' if result.success else 'failed'}",
                {
                    "operation_id": result.operation_id,
                    "entries_processed": result.processed_entries,
                    "entries_failed": result.failed_entries,
                    "batches_processed": result.batches_processed,
                    "duration_seconds": result.duration_seconds,
                    "integrity_verified": result.integrity_verified,
                    "error_summary": result.error_summary
                }
            )
        except Exception as e:
            logger.warning(f"Failed to audit re-encryption operation: {e}")

    def _save_checkpoint(self, checkpoint: ReencryptionCheckpoint):
        """Save checkpoint to disk."""
        checkpoint_file = self.checkpoint_dir / f"{checkpoint.operation_id}.json"

        try:
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def load_checkpoint(self, operation_id: str) -> Optional[ReencryptionCheckpoint]:
        """Load checkpoint from disk."""
        checkpoint_file = self.checkpoint_dir / f"{operation_id}.json"

        if not checkpoint_file.exists():
            return None

        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return ReencryptionCheckpoint.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load checkpoint {operation_id}: {e}")
            return None

    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """List all available checkpoints."""
        checkpoints = []

        try:
            for checkpoint_file in self.checkpoint_dir.glob("*.json"):
                try:
                    with open(checkpoint_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    checkpoints.append({
                        "operation_id": data["operation_id"],
                        "status": data["status"],
                        "phase": data["phase"],
                        "source_file": data["source_file"],
                        "start_time": data["start_time"],
                        "last_update": data["last_update"],
                        "progress": f"{data['processed_entries']}/{data['total_entries']}"
                    })
                except Exception as e:
                    logger.warning(f"Failed to read checkpoint {checkpoint_file}: {e}")

        except Exception as e:
            logger.error(f"Failed to list checkpoints: {e}")

        return checkpoints

    def cleanup_checkpoints(self, max_age_days: int = 7):
        """Clean up old checkpoints."""
        try:
            cutoff_time = datetime.now(timezone.utc).timestamp() - (max_age_days * 24 * 60 * 60)

            for checkpoint_file in self.checkpoint_dir.glob("*.json"):
                if checkpoint_file.stat().st_mtime < cutoff_time:
                    checkpoint_file.unlink()
                    logger.debug(f"Cleaned up old checkpoint: {checkpoint_file}")

        except Exception as e:
            logger.error(f"Failed to cleanup checkpoints: {e}")


# Convenience functions
def reencrypt_audit_log(source_file: str, retiring_key_id: str, active_key_id: str,
                       key_provider: Optional[KeyProvider] = None,
                       resume_from: Optional[str] = None) -> ReencryptionResult:
    """
    Convenience function to re-encrypt an audit log file.

    Args:
        source_file: Path to encrypted audit log
        retiring_key_id: ID of retiring key
        active_key_id: ID of active key
        key_provider: Optional key provider
        resume_from: Optional checkpoint to resume from

    Returns:
        ReencryptionResult
    """
    tool = LogReencryptionTool(key_provider)
    return tool.reencrypt_log_file(source_file, retiring_key_id, active_key_id, resume_from)


def get_reencryption_checkpoints() -> List[Dict[str, Any]]:
    """Get list of available re-encryption checkpoints."""
    tool = LogReencryptionTool()
    return tool.list_checkpoints()


__all__ = [
    "LogReencryptionTool",
    "ReencryptionResult",
    "ReencryptionStatus",
    "ReencryptionPhase",
    "ReencryptionBatch",
    "ReencryptionCheckpoint",
    "reencrypt_audit_log",
    "get_reencryption_checkpoints",
]
