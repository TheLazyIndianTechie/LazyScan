#!/usr/bin/env python3
"""
Retention policy engine for LazyScan cache management.
Handles age-based cleanup, safety classification, and admin privilege checking.
"""

import os
import time
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from ..core.cache_targets import CacheTarget, SafetyLevel
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class CleanupResult(Enum):
    """Result of a cleanup operation."""
    SUCCESS = "success"
    SKIPPED = "skipped"
    FAILED = "failed"
    REQUIRES_ADMIN = "requires_admin"


@dataclass
class CleanupOperation:
    """Represents a single cleanup operation."""
    target: CacheTarget
    files_to_delete: List[Path]
    total_size_mb: float
    result: CleanupResult
    error_message: Optional[str] = None

    @property
    def is_successful(self) -> bool:
        """Check if the operation was successful."""
        return self.result == CleanupResult.SUCCESS

    @property
    def is_skipped(self) -> bool:
        """Check if the operation was skipped."""
        return self.result == CleanupResult.SKIPPED


class RetentionPolicyEngine:
    """Engine for applying retention policies to cache targets."""

    def __init__(self, security_config: Dict[str, Any]):
        """
        Initialize the retention policy engine.

        Args:
            security_config: Security configuration dictionary
        """
        self.security_config = security_config
        self.allow_admin_operations = security_config.get("allow_admin_operations", False)
        self.confirm_deletions = security_config.get("confirm_deletions", True)
        self.safe_delete_enabled = security_config.get("safe_delete_enabled", True)

    def apply_retention_policies(
        self,
        cache_targets: List[CacheTarget],
        dry_run: bool = True,
        force: bool = False
    ) -> List[CleanupOperation]:
        """
        Apply retention policies to cache targets.

        Args:
            cache_targets: List of cache targets to process
            dry_run: If True, only simulate operations
            force: If True, skip safety confirmations

        Returns:
            List of cleanup operations performed
        """
        operations = []

        for target in cache_targets:
            if not target.enabled:
                logger.debug(f"Skipping disabled target: {target.path}")
                operations.append(CleanupOperation(
                    target=target,
                    files_to_delete=[],
                    total_size_mb=0.0,
                    result=CleanupResult.SKIPPED,
                    error_message="Target disabled"
                ))
                continue

            operation = self._process_cache_target(target, dry_run, force)
            operations.append(operation)

        return operations

    def _process_cache_target(
        self,
        target: CacheTarget,
        dry_run: bool,
        force: bool
    ) -> CleanupOperation:
        """
        Process a single cache target for cleanup.

        Args:
            target: Cache target to process
            dry_run: If True, only simulate operations
            force: If True, skip safety confirmations

        Returns:
            Cleanup operation result
        """
        try:
            # Check admin requirements
            if target.requires_admin and not self.allow_admin_operations:
                return CleanupOperation(
                    target=target,
                    files_to_delete=[],
                    total_size_mb=0.0,
                    result=CleanupResult.REQUIRES_ADMIN,
                    error_message="Admin privileges required but not allowed"
                )

            # Check safety level
            if not force and not self._is_safe_to_clean(target):
                return CleanupOperation(
                    target=target,
                    files_to_delete=[],
                    total_size_mb=0.0,
                    result=CleanupResult.SKIPPED,
                    error_message=f"Safety level {target.safety_level.value} requires confirmation"
                )

            # Find files to delete
            files_to_delete = self._find_expired_files(target)

            if not files_to_delete:
                return CleanupOperation(
                    target=target,
                    files_to_delete=[],
                    total_size_mb=0.0,
                    result=CleanupResult.SKIPPED,
                    error_message="No expired files found"
                )

            # Calculate total size
            total_size = sum(self._get_file_size(f) for f in files_to_delete)

            # Perform cleanup if not dry run
            if not dry_run:
                success = self._perform_cleanup(files_to_delete, target)
                result = CleanupResult.SUCCESS if success else CleanupResult.FAILED
                error_msg = None if success else "Cleanup operation failed"
            else:
                result = CleanupResult.SUCCESS  # Dry run always "succeeds"
                error_msg = None

            return CleanupOperation(
                target=target,
                files_to_delete=files_to_delete,
                total_size_mb=total_size,
                result=result,
                error_message=error_msg
            )

        except Exception as e:
            logger.error(f"Error processing cache target {target.path}: {e}")
            return CleanupOperation(
                target=target,
                files_to_delete=[],
                total_size_mb=0.0,
                result=CleanupResult.FAILED,
                error_message=str(e)
            )

    def _is_safe_to_clean(self, target: CacheTarget) -> bool:
        """
        Determine if it's safe to clean this cache target.

        Args:
            target: Cache target to check

        Returns:
            True if safe to clean
        """
        # Safe and caution levels are generally okay
        if target.safety_level in [SafetyLevel.SAFE, SafetyLevel.CAUTION]:
            return True

        # Dangerous operations require explicit confirmation
        if target.safety_level == SafetyLevel.DANGEROUS:
            return False

        return False

    def _find_expired_files(self, target: CacheTarget) -> List[Path]:
        """
        Find files in the cache target that have expired based on retention policy.

        Args:
            target: Cache target to scan

        Returns:
            List of expired files
        """
        if not target.path.exists():
            return []

        expired_files = []

        try:
            if target.path.is_file():
                if target.is_expired:
                    expired_files.append(target.path)
            elif target.path.is_dir():
                # For directories, check each file individually
                for file_path in target.path.rglob("*"):
                    if file_path.is_file():
                        # Create a temporary target for this file
                        file_target = CacheTarget(
                            path=file_path,
                            category=target.category,
                            retention_days=target.retention_days,
                            safety_level=target.safety_level,
                            requires_admin=target.requires_admin
                        )
                        if file_target.is_expired:
                            expired_files.append(file_path)
        except (OSError, PermissionError) as e:
            logger.warning(f"Permission error scanning {target.path}: {e}")

        return expired_files

    def _get_file_size(self, file_path: Path) -> float:
        """Get file size in MB."""
        try:
            return file_path.stat().st_size / (1024 * 1024)
        except (OSError, PermissionError):
            return 0.0

    def _perform_cleanup(self, files_to_delete: List[Path], target: CacheTarget) -> bool:
        """
        Perform the actual cleanup operation.

        Args:
            files_to_delete: List of files to delete
            target: Cache target being cleaned

        Returns:
            True if cleanup was successful
        """
        try:
            for file_path in files_to_delete:
                if file_path.exists():
                    if self.safe_delete_enabled:
                        # Use safe delete (move to trash/recycle bin)
                        self._safe_delete(file_path)
                    else:
                        # Direct deletion
                        if file_path.is_file():
                            file_path.unlink()
                        elif file_path.is_dir():
                            shutil.rmtree(file_path)

            logger.info(f"Cleaned {len(files_to_delete)} files from {target.path}")
            return True

        except Exception as e:
            logger.error(f"Failed to clean {target.path}: {e}")
            return False

    def _safe_delete(self, file_path: Path) -> None:
        """
        Perform safe deletion (move to trash/recycle bin).

        Args:
            file_path: File to safely delete
        """
        try:
            # For now, just use direct deletion
            # In a full implementation, this would integrate with platform-specific
            # trash/recycle bin functionality
            if file_path.is_file():
                file_path.unlink()
            elif file_path.is_dir():
                shutil.rmtree(file_path)
        except Exception as e:
            logger.warning(f"Safe delete failed for {file_path}: {e}")
            raise

    def get_cleanup_summary(self, operations: List[CleanupOperation]) -> Dict[str, Any]:
        """
        Generate a summary of cleanup operations.

        Args:
            operations: List of cleanup operations

        Returns:
            Summary dictionary
        """
        total_files = sum(len(op.files_to_delete) for op in operations)
        total_size = sum(op.total_size_mb for op in operations)
        successful_ops = sum(1 for op in operations if op.is_successful)
        skipped_ops = sum(1 for op in operations if op.is_skipped)
        failed_ops = len(operations) - successful_ops - skipped_ops

        return {
            "total_operations": len(operations),
            "successful_operations": successful_ops,
            "skipped_operations": skipped_ops,
            "failed_operations": failed_ops,
            "total_files_deleted": total_files,
            "total_size_mb": total_size,
            "operations": [
                {
                    "target": str(op.target.path),
                    "category": op.target.category,
                    "safety_level": op.target.safety_level.value,
                    "files_deleted": len(op.files_to_delete),
                    "size_mb": op.total_size_mb,
                    "result": op.result.value,
                    "error_message": op.error_message
                }
                for op in operations
            ]
        }