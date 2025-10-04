#!/usr/bin/env python3
"""
Security and Safety Module for LazyScan

This module provides comprehensive security safeguards to prevent accidental
deletion of critical user data and protect against security vulnerabilities.

Author: Security Enhancement for LazyScan
Version: 1.0.0
"""

import os
import re
import shutil
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Base exception for security-related errors"""

    pass


class PathValidationError(SecurityError):
    """Raised when path validation fails"""

    pass


class PermissionError(SecurityError):
    """Raised when permission checks fail"""

    pass


class BackupError(SecurityError):
    """Raised when backup operations fail"""

    pass


class PathValidator:
    """
    Secure path validation to prevent path traversal attacks and ensure
    operations only occur within allowed directories.
    """

    def __init__(self):
        # Define allowed root directories for cache operations
        self.allowed_cache_roots = {
            # macOS cache directories
            os.path.expanduser("~/Library/Caches"),
            os.path.expanduser("~/Library/Application Support"),
            os.path.expanduser("~/Library/Logs"),
            "/System/Library/Caches",
            "/Library/Caches",
            "/private/var/folders",  # System temp directories
            # Development cache directories
            os.path.expanduser("~/Library/Developer"),
            # User-specified project directories (will be added dynamically)
        }

        # Critical system paths that should NEVER be deleted
        self.forbidden_paths = {
            "/",
            "/System",
            "/usr",
            "/bin",
            "/sbin",
            "/etc",
            "/var/db",
            "/private/etc",
            os.path.expanduser("~"),
            os.path.expanduser("~/Documents"),
            os.path.expanduser("~/Desktop"),
            os.path.expanduser("~/Downloads"),
            os.path.expanduser("~/Pictures"),
            os.path.expanduser("~/Music"),
            os.path.expanduser("~/Movies"),
        }

        # Safe cache keywords that indicate cache directories
        self.safe_cache_keywords = {
            "cache",
            "temp",
            "tmp",
            "log",
            "logs",
            "crash",
            "crashes",
            "intermediate",
            "derived",
            "build",
            "obj",
            "bin",
            "library",
        }

    def add_allowed_root(self, path: str) -> None:
        """Add a new allowed root directory (e.g., for project scanning)"""
        normalized_path = os.path.realpath(os.path.expanduser(path))
        self.allowed_cache_roots.add(normalized_path)
        logger.info(f"Added allowed root: {normalized_path}")

    def is_safe_path(self, path: str) -> Tuple[bool, str]:
        """
        Comprehensive path safety validation.

        Returns:
            Tuple[bool, str]: (is_safe, reason)
        """
        try:
            # Normalize and resolve the path
            normalized_path = os.path.realpath(os.path.expanduser(path))

            # Check if path exists
            if not os.path.exists(normalized_path):
                return False, f"Path does not exist: {normalized_path}"

            # Check against forbidden paths
            for forbidden in self.forbidden_paths:
                forbidden_real = os.path.realpath(os.path.expanduser(forbidden))
                if normalized_path == forbidden_real or normalized_path.startswith(
                    forbidden_real + os.sep
                ):
                    return False, f"Path is in forbidden directory: {forbidden}"

            # Check if path is within allowed roots
            is_within_allowed = False
            for allowed_root in self.allowed_cache_roots:
                allowed_real = os.path.realpath(os.path.expanduser(allowed_root))
                if normalized_path.startswith(allowed_real):
                    is_within_allowed = True
                    break

            if not is_within_allowed:
                # Check if path contains safe cache keywords
                path_lower = normalized_path.lower()
                has_cache_keyword = any(
                    keyword in path_lower for keyword in self.safe_cache_keywords
                )

                if not has_cache_keyword:
                    return (
                        False,
                        "Path is not within allowed roots and doesn't contain cache keywords",
                    )

            # Additional safety checks
            if self._is_system_critical(normalized_path):
                return False, "Path appears to be system-critical"

            return True, "Path is safe for cache operations"

        except Exception as e:
            return False, f"Path validation error: {str(e)}"

    def _is_system_critical(self, path: str) -> bool:
        """Check if path contains system-critical files"""
        critical_patterns = [
            r"/System/",
            r"/usr/bin",
            r"/usr/sbin",
            r"/bin/",
            r"/sbin/",
            r"/etc/",
            r"kernel",
            r"boot",
        ]

        path_lower = path.lower()
        return any(re.search(pattern, path_lower) for pattern in critical_patterns)

    def validate_paths(self, paths: List[str]) -> Dict[str, Tuple[bool, str]]:
        """Validate multiple paths and return results"""
        results = {}
        for path in paths:
            results[path] = self.is_safe_path(path)
        return results


class InputSanitizer:
    """
    Input sanitization and validation for user inputs.
    """

    @staticmethod
    def sanitize_path_input(user_input: str, max_length: int = 512) -> str:
        """Sanitize user path input"""
        if not user_input:
            return ""

        # Limit length
        sanitized = user_input[:max_length]

        # Remove dangerous characters but keep path separators
        sanitized = re.sub(r"[^\w\s\-_./~]", "", sanitized)

        # Remove multiple consecutive dots (potential path traversal)
        sanitized = re.sub(r"\.{2,}", ".", sanitized)

        # Strip whitespace
        sanitized = sanitized.strip()

        return sanitized

    @staticmethod
    def sanitize_selection_input(user_input: str) -> str:
        """Sanitize user selection input (numbers, commas, spaces)"""
        if not user_input:
            return ""

        # Only allow numbers, commas, spaces, and basic separators
        sanitized = re.sub(r"[^0-9,\s\-]", "", user_input)

        return sanitized.strip()

    @staticmethod
    def validate_input_length(user_input: str, max_length: int = 256) -> bool:
        """Validate input length"""
        return len(user_input) <= max_length


class BackupManager:
    """
    Comprehensive backup system for files before deletion.
    """

    def __init__(self, backup_dir: Optional[str] = None):
        if backup_dir:
            self.backup_root = Path(backup_dir)
        else:
            self.backup_root = Path.home() / ".config" / "lazyscan" / "backups"

        self.backup_root.mkdir(parents=True, exist_ok=True)
        self.backup_index_file = self.backup_root / "backup_index.json"
        self.backup_index = self._load_backup_index()

    def _load_backup_index(self) -> Dict:
        """Load backup index from file"""
        if self.backup_index_file.exists():
            try:
                with open(self.backup_index_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load backup index: {e}")
        return {"backups": [], "version": "1.0"}

    def _save_backup_index(self) -> None:
        """Save backup index to file"""
        try:
            with open(self.backup_index_file, "w") as f:
                json.dump(self.backup_index, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save backup index: {e}")

    def create_backup(self, source_path: str, operation_id: str) -> Optional[str]:
        """
        Create backup of file/directory before deletion.

        Args:
            source_path: Path to backup
            operation_id: Unique identifier for this operation

        Returns:
            Backup path if successful, None if failed
        """
        try:
            source = Path(source_path)
            if not source.exists():
                logger.warning(f"Source path does not exist: {source_path}")
                return None

            # Create timestamp-based backup directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_session_dir = self.backup_root / f"{operation_id}_{timestamp}"
            backup_session_dir.mkdir(parents=True, exist_ok=True)

            # Calculate relative path from source root
            backup_target = backup_session_dir / source.name

            # Perform backup
            if source.is_file():
                shutil.copy2(source, backup_target)
            else:
                shutil.copytree(source, backup_target, dirs_exist_ok=True)

            # Record backup in index
            backup_record = {
                "id": operation_id,
                "timestamp": timestamp,
                "original_path": str(source),
                "backup_path": str(backup_target),
                "size": self._get_size(source),
                "checksum": self._calculate_checksum(source),
            }

            self.backup_index["backups"].append(backup_record)
            self._save_backup_index()

            logger.info(f"Created backup: {source} -> {backup_target}")
            return str(backup_target)

        except Exception as e:
            logger.error(f"Backup failed for {source_path}: {e}")
            raise BackupError(f"Failed to create backup: {e}")

    def _get_size(self, path: Path) -> int:
        """Get size of file or directory"""
        if path.is_file():
            return path.stat().st_size
        else:
            total = 0
            for item in path.rglob("*"):
                if item.is_file():
                    total += item.stat().st_size
            return total

    def _calculate_checksum(self, path: Path) -> str:
        """Calculate checksum for verification"""
        if path.is_file():
            with open(path, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        else:
            # For directories, create checksum of file list and sizes
            file_info = []
            for item in sorted(path.rglob("*")):
                if item.is_file():
                    file_info.append(f"{item.relative_to(path)}:{item.stat().st_size}")
            return hashlib.md5("\n".join(file_info).encode()).hexdigest()

    def restore_backup(self, backup_id: str) -> bool:
        """Restore a backup by ID"""
        for backup in self.backup_index["backups"]:
            if backup["id"] == backup_id:
                try:
                    backup_path = Path(backup["backup_path"])
                    original_path = Path(backup["original_path"])

                    if backup_path.exists():
                        if backup_path.is_file():
                            shutil.copy2(backup_path, original_path)
                        else:
                            shutil.copytree(
                                backup_path, original_path, dirs_exist_ok=True
                            )

                        logger.info(
                            f"Restored backup: {backup_path} -> {original_path}"
                        )
                        return True
                    else:
                        logger.error(f"Backup file not found: {backup_path}")
                        return False

                except Exception as e:
                    logger.error(f"Restore failed: {e}")
                    return False

        logger.error(f"Backup not found: {backup_id}")
        return False

    def list_backups(self) -> List[Dict]:
        """List all available backups"""
        return self.backup_index["backups"]

    def cleanup_old_backups(self, days_to_keep: int = 30) -> None:
        """Clean up backups older than specified days"""
        cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)

        backups_to_remove = []
        for backup in self.backup_index["backups"]:
            backup_time = datetime.strptime(
                backup["timestamp"], "%Y%m%d_%H%M%S"
            ).timestamp()
            if backup_time < cutoff_date:
                backups_to_remove.append(backup)

        for backup in backups_to_remove:
            try:
                backup_path = Path(backup["backup_path"])
                if backup_path.exists():
                    if backup_path.is_file():
                        backup_path.unlink()
                    else:
                        shutil.rmtree(backup_path)

                self.backup_index["backups"].remove(backup)
                logger.info(f"Cleaned up old backup: {backup['id']}")

            except Exception as e:
                logger.error(f"Failed to cleanup backup {backup['id']}: {e}")

        self._save_backup_index()


# Global instances
path_validator = PathValidator()
input_sanitizer = InputSanitizer()
backup_manager = BackupManager()


# Convenience functions
def validate_path(path: str) -> Tuple[bool, str]:
    """Validate a single path for safety"""
    return path_validator.is_safe_path(path)


def validate_paths(paths: List[str]) -> Dict[str, Tuple[bool, str]]:
    """Validate multiple paths"""
    return path_validator.validate_paths(paths)


def sanitize_input(user_input: str, input_type: str = "path") -> str:
    """Sanitize user input based on type"""
    if input_type == "path":
        return input_sanitizer.sanitize_path_input(user_input)
    elif input_type == "selection":
        return input_sanitizer.sanitize_selection_input(user_input)
    else:
        return user_input.strip()


def create_backup(path: str, operation_id: str) -> Optional[str]:
    """Create backup of path"""
    return backup_manager.create_backup(path, operation_id)


def restore_backup(backup_id: str) -> bool:
    """Restore a backup"""
    return backup_manager.restore_backup(backup_id)
