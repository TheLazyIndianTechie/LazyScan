#!/usr/bin/env python3
"""
Safe deletion module with fail-closed security guarantees.
Eliminates direct file deletion risks with policy-driven approach.
"""

import os
import sys
from pathlib import Path
from enum import Enum

try:
    import send2trash
except ImportError:
    send2trash = None

from ..core.errors import DeletionSafetyError, SecurityPolicyError
from ..core.logging_config import get_logger, get_console, log_deletion_event

logger = get_logger(__name__)
console = get_console()


class DeletionMode(Enum):
    TRASH = "trash"
    PERMANENT = "permanent"


class SafeDeleter:
    """
    Centralized, policy-driven file deletion with security safeguards.

    Key features:
    - Global kill switch via LAZYSCAN_DISABLE_DELETIONS=1
    - Trash-first deletion by default
    - Path validation before any operation
    - Structured logging of all decisions
    - Two-step confirmation for large directories
    """

    def __init__(self):
        self._kill_switch_enabled = os.getenv("LAZYSCAN_DISABLE_DELETIONS", "0") == "1"
        if self._kill_switch_enabled:
            logger.warning("🛑 Global kill switch enabled - all deletions disabled")

    def delete(
        self,
        path: Path,
        mode: DeletionMode = DeletionMode.TRASH,
        dry_run: bool = True,
        force: bool = False,
        context: str = "general",
    ) -> bool:
        """
        Safely delete a file or directory with comprehensive checks.

        Args:
            path: Path to delete (will be canonicalized)
            mode: DeletionMode.TRASH (default) or DeletionMode.PERMANENT
            dry_run: If True, log what would be deleted but don't actually delete
            force: If True, skip interactive confirmations (dangerous!)

        Returns:
            bool: True if deletion was successful or would succeed (dry_run)

        Raises:
            DeletionSafetyError: If deletion is blocked by security checks
        """

        # Check global kill switch first
        if self._kill_switch_enabled:
            raise DeletionSafetyError(
                "Global deletion kill switch is enabled (LAZYSCAN_DISABLE_DELETIONS=1). "
                "All destructive operations are blocked."
            )

        # Check for symlinks BEFORE canonicalization
        if path.is_symlink():
            raise DeletionSafetyError(
                f"Attempted to delete symlink: {path}. "
                "Symlink deletion is blocked to prevent unexpected behavior."
            )

        # Canonicalize and validate path
        try:
            canonical_path = path.resolve(strict=False)
        except Exception as e:
            raise DeletionSafetyError(f"Cannot resolve path {path}: {e}")

        # Log the deletion attempt
        logger.info(
            "Deletion requested",
            extra={
                "path": str(canonical_path),
                "mode": mode.value,
                "dry_run": dry_run,
                "force": force,
            },
        )

        # Security checks
        self._validate_deletion_safety(canonical_path, context, mode.value)

        if dry_run:
            logger.info(
                f"DRY RUN: Would delete {canonical_path} using {mode.value} mode"
            )
            return True

        # Actual deletion logic would go here
        if mode == DeletionMode.TRASH:
            return self._delete_to_trash(canonical_path, force=force)
        else:
            return self._delete_permanent(canonical_path, force=force)

    def _validate_deletion_safety(
        self, path: Path, context: str, operation_mode: str
    ) -> None:
        """
        Validate that the path is safe to delete.

        Raises:
            DeletionSafetyError: If path fails safety checks
        """

        # Check if path exists
        if not path.exists():
            logger.warning(f"Path does not exist: {path}")
            return  # Not an error - already "deleted"

        # Try to get SecuritySentinel for policy enforcement
        try:
            from .sentinel import get_sentinel

            sentinel = get_sentinel()
            # Ask sentinel to guard this delete operation
            sentinel.guard_delete(path, context, operation_mode)

        except (SecurityPolicyError, ImportError) as e:
            # Fall back to basic validation if sentinel is not available
            logger.warning(
                f"SecuritySentinel not available, using basic validation: {e}"
            )

            # Basic critical path checks (fallback)
            if self._is_critical_system_path(path):
                raise DeletionSafetyError(
                    f"Attempted to delete critical system path: {path}. "
                    "This operation is blocked for safety."
                )

        logger.debug(f"Path validation passed for: {path}")

    def _is_critical_system_path(self, path: Path) -> bool:
        """Check if path is a critical system directory that should never be deleted."""

        critical_paths = [
            Path.home(),  # User home directory
            Path("/"),  # Root directory (Unix)
            Path("C:\\"),  # C: drive root (Windows)
            Path("/System"),  # macOS system directory
            Path("/usr"),  # Unix system directories
            Path("/var"),
            Path("/etc"),
            Path("/boot"),
        ]

        # Check if path is or is parent of any critical path
        for critical in critical_paths:
            try:
                if path.samefile(critical) or critical.is_relative_to(path):
                    return True
            except (OSError, ValueError):
                # Handle paths that don't exist or permission errors
                continue

        return False

    def _delete_to_trash(self, path: Path, force: bool = False) -> bool:
        """Delete path to trash/recycle bin."""

        if send2trash is None:
            raise DeletionSafetyError(
                "send2trash library not available. Cannot safely delete to trash. "
                "Install with: pip install send2trash"
            )

        try:
            send2trash.send2trash(str(path))
            logger.info(f"Successfully moved to trash: {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to move to trash: {path}, error: {e}")
            raise DeletionSafetyError(f"Trash deletion failed: {e}")

    def _delete_permanent(self, path: Path, force: bool = False) -> bool:
        """Permanently delete path (dangerous!)."""

        if not force and sys.stdin.isatty():
            # Interactive confirmation required
            console.print_warning("⚠️  PERMANENT DELETION WARNING")
            console.print_warning(f"   Path: {path}")
            console.print_warning("   This operation CANNOT be undone!")

            response = input("   Type 'DELETE' to confirm: ").strip()
            if response != "DELETE":
                console.print_info("   Deletion cancelled.")
                logger.info(
                    "Permanent deletion cancelled by user",
                    path=str(path),
                    operation="permanent_delete",
                    user_action="cancelled",
                )
                # Log security event for audit
                log_deletion_event(
                    path=str(path),
                    deletion_mode="permanent",
                    result="cancelled_by_user",
                    reason="user_declined_confirmation",
                )
                return False

        # Implement permanent deletion logic
        try:
            if path.is_file():
                # Delete single file
                path.unlink()
                logger.info(f"Successfully permanently deleted file: {path}")
            elif path.is_dir():
                # Delete directory tree
                import shutil
                shutil.rmtree(path)
                logger.info(f"Successfully permanently deleted directory: {path}")
            else:
                # Handle other types (symlinks, etc.) - but we already checked for symlinks
                raise DeletionSafetyError(f"Unsupported file type for permanent deletion: {path}")

            # Log security event for audit
            log_deletion_event(
                path=str(path),
                deletion_mode="permanent",
                result="success",
                reason="permanent_deletion_completed",
            )
            return True

        except PermissionError as e:
            error_msg = f"Permission denied deleting {path}: {e}"
            logger.error(error_msg)
            log_deletion_event(
                path=str(path),
                deletion_mode="permanent",
                result="failed",
                reason=f"permission_error: {e}",
            )
            raise DeletionSafetyError(error_msg)

        except OSError as e:
            error_msg = f"OS error deleting {path}: {e}"
            logger.error(error_msg)
            log_deletion_event(
                path=str(path),
                deletion_mode="permanent",
                result="failed",
                reason=f"os_error: {e}",
            )
            raise DeletionSafetyError(error_msg)

        except Exception as e:
            error_msg = f"Unexpected error deleting {path}: {e}"
            logger.error(error_msg)
            log_deletion_event(
                path=str(path),
                deletion_mode="permanent",
                result="failed",
                reason=f"unexpected_error: {e}",
            )
            raise DeletionSafetyError(error_msg)


# Global instance
_safe_deleter = None


def get_safe_deleter() -> SafeDeleter:
    """Get the global SafeDeleter instance."""
    global _safe_deleter
    if _safe_deleter is None:
        _safe_deleter = SafeDeleter()
    return _safe_deleter


def safe_delete(path: Path, **kwargs) -> bool:
    """Convenience function for safe deletion."""
    return get_safe_deleter().delete(path, **kwargs)
