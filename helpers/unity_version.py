"""Unity Editor version detection and management module.

This module provides functionality to detect Unity Editor versions from project files
and installed Unity Hub installations across different platforms.
"""

import os
import re
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from lazyscan.core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class UnityVersion:
    """Represents a Unity Editor version with semantic information."""
    major: int
    minor: int
    patch: int
    revision: Optional[str] = None
    full_version: str = ""

    def __str__(self) -> str:
        """Return the full version string."""
        return self.full_version or f"{self.major}.{self.minor}.{self.patch}"

    def __lt__(self, other: 'UnityVersion') -> bool:
        """Compare versions for sorting."""
        if not isinstance(other, UnityVersion):
            return NotImplemented
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __eq__(self, other: object) -> bool:
        """Check version equality."""
        if not isinstance(other, UnityVersion):
            return False
        return (self.major, self.minor, self.patch, self.revision) == \
               (other.major, other.minor, other.patch, other.revision)


def parse_project_version(project_path: Path) -> Optional[UnityVersion]:
    """Parse Unity version from ProjectSettings/ProjectVersion.txt.

    Args:
        project_path: Path to the Unity project root directory.

    Returns:
        UnityVersion object if parsing succeeds, None otherwise.
    """
    version_file = project_path / "ProjectSettings" / "ProjectVersion.txt"

    if not version_file.exists():
        logger.debug(f"ProjectVersion.txt not found at {version_file}")
        return None

    try:
        with open(version_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse the version line - format: m_EditorVersion: 2021.3.15f1
        # or newer format: m_EditorVersionWithRevision: 2021.3.15f1 (b3b2c6512324)
        version_match = re.search(r'm_EditorVersion(?:WithRevision)?:\s*([^\s\n]+)', content)
        if not version_match:
            logger.warning(f"Could not parse version from {version_file}")
            return None

        version_str = version_match.group(1).strip()

        # Parse semantic version components
        # Examples: 2021.3.15f1, 2022.2.0a1, 2023.1.0b5
        version_pattern = r'^(\d{4})\.(\d+)\.(\d+)([a-zA-Z]?\d*)$'
        match = re.match(version_pattern, version_str)

        if not match:
            logger.warning(f"Version string '{version_str}' does not match expected format")
            return None

        major = int(match.group(1))
        minor = int(match.group(2))
        patch = int(match.group(3))
        revision = match.group(4) if match.group(4) else None

        return UnityVersion(
            major=major,
            minor=minor,
            patch=patch,
            revision=revision,
            full_version=version_str
        )

    except Exception as e:
        logger.error(f"Failed to parse project version from {version_file}: {e}")
        return None


def get_unity_installations() -> List[Dict[str, Any]]:
    """Get list of installed Unity Editor versions from Unity Hub.

    Returns:
        List of dictionaries containing installation information.
        Each dict contains: 'version', 'path', 'architecture' (if available)
    """
    installations = []

    try:
        # Unity Hub stores installation info in different locations per platform
        import platform
        system = platform.system().lower()

        if system == "darwin":  # macOS
            editors_path = Path.home() / "Library" / "Application Support" / "UnityHub" / "editors"
        elif system == "windows":
            editors_path = Path.home() / "AppData" / "Roaming" / "UnityHub" / "editors"
        elif system == "linux":
            editors_path = Path.home() / ".config" / "unityhub" / "editors"
        else:
            logger.warning(f"Unsupported platform for Unity Hub detection: {system}")
            return installations

        if not editors_path.exists():
            logger.debug(f"Unity Hub editors directory not found at {editors_path}")
            return installations

        # Each subdirectory is a version (e.g., "2021.3.15f1")
        for version_dir in editors_path.iterdir():
            if version_dir.is_dir():
                version_str = version_dir.name

                # Try to parse the version to validate it's a proper Unity version
                try:
                    # Quick validation - should be in format YYYY.M.P[revision]
                    if re.match(r'^\d{4}\.\d+\.\d+[a-zA-Z]?\d*$', version_str):
                        installations.append({
                            'version': version_str,
                            'path': str(version_dir),
                            'architecture': _detect_architecture(version_dir)
                        })
                except Exception:
                    continue

        # Sort by version (newest first)
        installations.sort(key=lambda x: x['version'], reverse=True)

    except Exception as e:
        logger.error(f"Failed to detect Unity installations: {e}")

    return installations


def _detect_architecture(install_path: Path) -> Optional[str]:
    """Detect the architecture of a Unity installation.

    Args:
        install_path: Path to the Unity Editor installation directory.

    Returns:
        Architecture string ('x64', 'arm64', etc.) or None if undetected.
    """
    try:
        # Check for common architecture indicators
        if (install_path / "Unity.app" / "Contents" / "MacOS" / "Unity").exists():  # macOS
            # On macOS, check if it's Intel or Apple Silicon
            # This is a simplified check - in practice, you'd check the binary
            return "universal"  # Most modern Unity builds are universal binaries

        elif (install_path / "Editor" / "Unity.exe").exists():  # Windows
            # On Windows, check the executable architecture
            unity_exe = install_path / "Editor" / "Unity.exe"
            if unity_exe.exists():
                # This would require more complex PE file parsing
                # For now, assume x64 as it's the most common
                return "x64"

        elif (install_path / "Editor" / "Unity").exists():  # Linux
            # On Linux, check the ELF architecture
            unity_binary = install_path / "Editor" / "Unity"
            if unity_binary.exists():
                # This would require ELF parsing
                # For now, assume x64
                return "x64"

    except Exception as e:
        logger.debug(f"Failed to detect architecture for {install_path}: {e}")

    return None


def find_matching_unity_installation(project_version: UnityVersion) -> Optional[Dict[str, Any]]:
    """Find an installed Unity Editor that matches the project version.

    Args:
        project_version: The Unity version required by the project.

    Returns:
        Installation info dict if found, None otherwise.
    """
    installations = get_unity_installations()

    # First, try exact match
    for install in installations:
        if install['version'] == project_version.full_version:
            return install

    # If no exact match, try to find a compatible version
    # Unity projects are generally compatible with patch-level differences
    for install in installations:
        try:
            # Extract patch number from version string (e.g., "15f1" -> 15)
            patch_part = install['version'].split('.')[-1]
            patch_match = re.search(r'\d+', patch_part)
            if not patch_match:
                continue
            patch = int(patch_match.group(0))

            install_version = UnityVersion(
                major=project_version.major,
                minor=project_version.minor,
                patch=patch,
                full_version=install['version']
            )

            if install_version.major == project_version.major and \
               install_version.minor == project_version.minor:
                logger.info(f"Found compatible Unity installation: {install['version']} for project version {project_version}")
                return install

        except Exception:
            continue

    logger.warning(f"No compatible Unity installation found for version {project_version}")
    return None


def get_unity_cache_paths(version: Optional[UnityVersion] = None) -> Dict[str, str]:
    """Get Unity cache directory paths based on platform and version.

    Args:
        version: Unity version to determine cache paths for. If None, uses generic paths.

    Returns:
        Dictionary mapping cache type names to their paths.
    """
    import platform
    system = platform.system().lower()
    home = Path.home()

    cache_paths = {}

    if system == "darwin":  # macOS
        cache_paths.update({
            'global_cache': str(home / "Library" / "Unity" / "cache"),
            'package_cache': str(home / "Library" / "Unity" / "cache" / "packages"),
            'asset_store': str(home / "Library" / "Unity" / "Asset Store-5.x"),
        })

    elif system == "windows":
        cache_paths.update({
            'global_cache': str(home / "AppData" / "Local" / "Unity" / "cache"),
            'package_cache': str(home / "AppData" / "Local" / "Unity" / "cache" / "packages"),
            'asset_store': str(home / "AppData" / "Roaming" / "Unity" / "Asset Store-5.x"),
        })

    elif system == "linux":
        cache_paths.update({
            'global_cache': str(home / ".cache" / "unity3d"),
            'package_cache': str(home / ".cache" / "unity3d" / "Packages"),
            'asset_store': str(home / ".local" / "share" / "unity3d" / "Asset Store-5.x"),
        })

    # Version-specific paths if version is provided
    if version:
        version_suffix = f"{version.major}.{version.minor}"
        for cache_type, base_path in cache_paths.items():
            # Some caches have version-specific subdirectories
            versioned_path = Path(base_path) / version_suffix
            if versioned_path.exists():
                cache_paths[cache_type] = str(versioned_path)

    return cache_paths