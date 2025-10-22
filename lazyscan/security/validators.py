#!/usr/bin/env python3
"""
Path and input validation library for LazyScan.
Provides comprehensive path canonicalization and safety checks.
"""

import logging
import os
import re
import sys
from pathlib import Path
from typing import Union

from ..core.errors import PathValidationError

logger = logging.getLogger(__name__)

# Windows reserved device names
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}

# Default allowed roots per application context
DEFAULT_ALLOWED_ROOTS = {
    "unity": [
        "~/Library/Application Support/Unity",
        "~/Library/Caches/Unity",
        "~/Projects",
        "~/Documents/Unity Projects",
    ],
    "unreal": [
        # Non-default installations first (per user preference)
        "/Volumes/LazyGameDevs/Applications/Unreal/UE_5.5/",
        "/Volumes/LazyGameDevs/Applications/Unreal/UE_5.6",
        # Standard locations
        "~/Documents/Unreal Projects",
        "~/Library/Application Support/Epic",
        "~/Library/Caches/UnrealEngine",
        "/Applications/Epic Games",
        "/Users/Shared/Epic Games",
    ],
    "chrome": [
        "~/Library/Caches/Google/Chrome",
        "~/Library/Application Support/Google/Chrome",
        "~/Library/WebKit",
    ],
    "macos_caches": [
        "~/Library/Caches",
        "~/Library/Application Support",
        "~/Library/WebKit",
        "/var/folders",  # System temp directories
        "/tmp",
        "/private/tmp",
    ],
}

# System-critical paths that should never be deleted
CRITICAL_SYSTEM_PATHS = {
    "macos": [
        "/",
        "/System",
        "/usr",
        "/var",
        "/etc",
        "/bin",
        "/sbin",
        "/boot",
        "/Applications",
        "/Library",
        "/Users",
        "/Volumes",
    ],
    "windows": [
        "C:\\",
        "C:\\Windows",
        "C:\\Program Files",
        "C:\\Program Files (x86)",
        "C:\\Users",
        "C:\\ProgramData",
    ],
    "linux": [
        "/",
        "/usr",
        "/var",
        "/etc",
        "/bin",
        "/sbin",
        "/boot",
        "/home",
        "/root",
        "/opt",
        "/lib",
        "/lib64",
    ],
}


def canonicalize_path(path: Union[str, Path]) -> Path:
    """
    Canonicalize and expand a path with comprehensive validation.

    Args:
        path: Path to canonicalize (string or Path object)

    Returns:
        Path: Canonicalized Path object

    Raises:
        PathValidationError: If path is invalid or suspicious
    """
    if not path:
        raise PathValidationError("Path cannot be empty or None")

    # Convert to Path object
    if isinstance(path, str):
        path = Path(path)

    # Check for suspicious patterns before expansion
    path_str = str(path)

    # Block control characters and suspicious patterns
    if re.search(r"[\x00-\x1f\x7f]", path_str):
        raise PathValidationError(f"Path contains control characters: {path!r}")

    # Block mixed path separators (potential injection)
    if "\\" in path_str and "/" in path_str:
        raise PathValidationError(f"Path contains mixed separators: {path!r}")

    # Block trailing newlines or spaces
    if path_str != path_str.strip():
        raise PathValidationError(f"Path has leading/trailing whitespace: {path!r}")

    # Windows-specific validation
    if os.name == "nt":
        # Check for reserved device names
        parts = [p.upper() for p in path.parts]
        for part in parts:
            name = part.split(".")[0]  # Remove extension
            if name in WINDOWS_RESERVED_NAMES:
                raise PathValidationError(
                    f"Path contains Windows reserved name: {name}"
                )

        # Block trailing dots or spaces in components
        for part in path.parts:
            if part.endswith(".") or part.endswith(" "):
                raise PathValidationError(
                    f"Path component ends with dot/space: {part!r}"
                )

    try:
        # Expand user home directory
        expanded = path.expanduser()

        # Resolve to canonical form (but don't require existence)
        canonical = expanded.resolve(strict=False)

        logger.debug(f"Canonicalized {path} -> {canonical}")
        return canonical

    except (OSError, ValueError) as e:
        raise PathValidationError(f"Cannot canonicalize path {path}: {e}")


def is_within_allowed_roots(path: Path, allowed_roots: list[Path]) -> bool:
    """
    Check if a path is within any of the allowed root directories.
    Uses secure path comparison that prevents symlink traversal attacks.

    Args:
        path: Path to check (should be canonicalized)
        allowed_roots: List of allowed root paths (will be canonicalized)

    Returns:
        bool: True if path is within allowed roots
    """
    try:
        # Canonicalize the target path
        canonical_path = path.resolve(strict=False)

        for root in allowed_roots:
            try:
                # Canonicalize the root path
                canonical_root = canonicalize_path(root)

                # Check if path is relative to root
                canonical_path.relative_to(canonical_root)
                logger.debug(f"Path {path} is within allowed root {root}")
                return True

            except ValueError:
                # Path is not relative to this root, try next one
                continue
            except PathValidationError as e:
                logger.warning(f"Invalid root path {root}: {e}")
                continue

        logger.debug(f"Path {path} is NOT within any allowed roots")
        return False

    except Exception as e:
        logger.error(f"Error checking path {path} against allowed roots: {e}")
        return False


def is_symlink_or_reparse(path: Path) -> bool:
    """
    Check if path is a symlink, junction, or reparse point.

    Args:
        path: Path to check

    Returns:
        bool: True if path is a symlink/junction/reparse point
    """
    try:
        return path.is_symlink()
    except (OSError, ValueError):
        # If we can't determine, assume it's suspicious
        return True


def is_critical_system_path(path: Path) -> bool:
    """
    Check if path is a critical system directory that should never be modified.

    Args:
        path: Path to check (should be canonicalized)

    Returns:
        bool: True if path is a critical system path
    """
    try:
        canonical = path.resolve(strict=False)

        # Determine OS and get critical paths
        if sys.platform == "darwin":
            critical_paths = CRITICAL_SYSTEM_PATHS["macos"]
        elif os.name == "nt":
            critical_paths = CRITICAL_SYSTEM_PATHS["windows"]
        else:
            critical_paths = CRITICAL_SYSTEM_PATHS["linux"]

        # Check if path is or contains any critical path
        for critical_str in critical_paths:
            critical_path = Path(critical_str).resolve(strict=False)

            try:
                # Check if path is the same as critical path
                if canonical.samefile(critical_path):
                    return True

                # Check if critical path is relative to path (path is parent of critical)
                critical_path.relative_to(canonical)
                return True

            except (ValueError, OSError):
                # Not related to this critical path
                continue

        # Special case: user home directory
        try:
            home = Path.home().resolve(strict=False)
            if canonical.samefile(home):
                return True
        except (OSError, ValueError):
            pass

        return False

    except Exception as e:
        logger.error(f"Error checking critical path status for {path}: {e}")
        # When in doubt, consider it critical for safety
        return True


def validate_user_supplied_path(
    path: Union[str, Path], context: str = "general"
) -> Path:
    """
    Validate a user-supplied path with comprehensive safety checks.

    Args:
        path: User-supplied path to validate
        context: Context for validation ('unity', 'unreal', 'chrome', etc.)

    Returns:
        Path: Validated and canonicalized path

    Raises:
        PathValidationError: If path fails validation
    """
    if not path:
        raise PathValidationError("Path cannot be empty")

    # Canonicalize the path
    canonical = canonicalize_path(path)

    # Check for symlinks/junctions
    if is_symlink_or_reparse(Path(path)):  # Check original path
        raise PathValidationError(f"Symlinks and junctions are not allowed: {path}")

    # Check for critical system paths
    if is_critical_system_path(canonical):
        raise PathValidationError(f"Critical system path access denied: {canonical}")

    # Context-specific validation
    if context in DEFAULT_ALLOWED_ROOTS:
        allowed_roots = [Path(root) for root in DEFAULT_ALLOWED_ROOTS[context]]
        if not is_within_allowed_roots(canonical, allowed_roots):
            raise PathValidationError(
                f"Path {canonical} is not within allowed roots for context '{context}'"
            )

    logger.info(f"Path validation passed for {canonical} in context '{context}'")
    return canonical


def get_allowed_roots_for_context(context: str) -> list[Path]:
    """
    Get the allowed root paths for a given context.

    Args:
        context: Context name ('unity', 'unreal', 'chrome', etc.)

    Returns:
        List[Path]: List of allowed root paths (canonicalized)
    """
    roots = DEFAULT_ALLOWED_ROOTS.get(context, [])
    canonicalized = []

    for root in roots:
        try:
            canonical = canonicalize_path(root)
            canonicalized.append(canonical)
        except PathValidationError as e:
            logger.warning(f"Invalid root path {root} for context {context}: {e}")
            continue

    return canonicalized


def expand_unreal_engine_paths() -> list[Path]:
    """
    Get Unreal Engine installation paths, checking non-default locations first.
    Per user preference, always check these paths first:
    - /Volumes/LazyGameDevs/Applications/Unreal/UE_5.5/
    - /Volumes/LazyGameDevs/Applications/Unreal/UE_5.6

    Returns:
        List[Path]: List of potential Unreal Engine installation paths
    """
    paths = []

    # Non-default installations (user preference - check first)
    priority_paths = [
        "/Volumes/LazyGameDevs/Applications/Unreal/UE_5.5/",
        "/Volumes/LazyGameDevs/Applications/Unreal/UE_5.6",
    ]

    for path_str in priority_paths:
        path = Path(path_str)
        if path.exists():
            paths.append(path)
            logger.info(f"Found non-default Unreal installation: {path}")

    # Standard locations
    standard_paths = [
        "/Applications/Epic Games/UE_5.0",
        "/Applications/Epic Games/UE_5.1",
        "/Applications/Epic Games/UE_5.2",
        "/Applications/Epic Games/UE_5.3",
        "/Applications/Epic Games/UE_5.4",
        "/Applications/Epic Games/UE_5.5",
        "/Applications/Epic Games/UE_5.6",
        "~/Documents/Unreal Projects",
    ]

    for path_str in standard_paths:
        try:
            path = canonicalize_path(path_str)
            if path.exists():
                paths.append(path)
        except PathValidationError:
            continue

    # Environment variable override
    env_paths = os.getenv("LAZYSCAN_UNREAL_PATHS", "")
    if env_paths:
        for path_str in env_paths.split(os.pathsep):
            try:
                path = canonicalize_path(path_str.strip())
                if path.exists():
                    paths.append(path)
                    logger.info(f"Found Unreal installation from env: {path}")
            except PathValidationError:
                continue

    return paths


# Convenience functions for common validations


def validate_unity_path(path: Union[str, Path]) -> Path:
    """Validate a Unity project path."""
    return validate_user_supplied_path(path, "unity")


def validate_unreal_path(path: Union[str, Path]) -> Path:
    """Validate an Unreal Engine project path."""
    return validate_user_supplied_path(path, "unreal")


def validate_chrome_path(path: Union[str, Path]) -> Path:
    """Validate a Chrome cache path."""
    return validate_user_supplied_path(path, "chrome")


def validate_general_path(path: Union[str, Path]) -> Path:
    """Validate a general path with basic safety checks."""
    canonical = canonicalize_path(path)

    # Check for symlinks
    if is_symlink_or_reparse(Path(path)):
        raise PathValidationError(f"Symlinks are not allowed: {path}")

    # Check for critical system paths
    if is_critical_system_path(canonical):
        raise PathValidationError(f"Critical system path access denied: {canonical}")

    return canonical
