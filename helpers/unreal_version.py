"""Unreal Engine version resolution and project metadata parsing.

This module provides functionality to parse Unreal project metadata (.uproject files)
and resolve engine versions from Epic Games Launcher manifests.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from lazyscan.core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class UnrealProject:
    """Represents an Unreal Engine project with metadata and cache targets."""
    path: Path
    engine_version: Optional[str]
    caches: List['CacheTarget']
    name: str = ""
    uproject_file: Optional[Path] = None

    def __post_init__(self):
        if not self.name and self.uproject_file:
            self.name = self.uproject_file.stem


@dataclass
class CacheTarget:
    """Represents a cache directory target with safety flags."""
    name: str
    path: Path
    warn_on_delete: bool = False
    requires_backup: bool = False
    description: str = ""


def parse_uproject_metadata(uproject_path: Path) -> Dict[str, Any]:
    """Parse .uproject file and extract metadata.

    Args:
        uproject_path: Path to the .uproject file

    Returns:
        Dictionary containing project metadata

    Raises:
        FileNotFoundError: If .uproject file doesn't exist
        json.JSONDecodeError: If .uproject file is not valid JSON
        ValueError: If required fields are missing
    """
    if not uproject_path.exists():
        raise FileNotFoundError(f".uproject file not found: {uproject_path}")

    try:
        with open(uproject_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in .uproject file {uproject_path}: {e}")

    # Validate required fields
    if not isinstance(metadata, dict):
        raise ValueError(f".uproject file {uproject_path} does not contain a valid object")

    return metadata


def resolve_engine_version(engine_association: str) -> Optional[str]:
    """Resolve engine version from EngineAssociation string.

    Args:
        engine_association: EngineAssociation value from .uproject

    Returns:
        Resolved engine version string or None if not found
    """
    if not engine_association:
        return None

    # Handle different EngineAssociation formats
    if engine_association.startswith('{'):
        # JSON format - parse and extract version
        try:
            assoc_data = json.loads(engine_association)
            return assoc_data.get('Version', assoc_data.get('Identifier'))
        except json.JSONDecodeError:
            pass

    # Direct version string (e.g., "5.3", "4.27")
    if engine_association.replace('.', '').replace('-', '').isdigit():
        return engine_association

    # Handle common identifiers
    version_map = {
        'UE_5.3': '5.3',
        'UE_5.2': '5.2',
        'UE_5.1': '5.1',
        'UE_5.0': '5.0',
        'UE_4.27': '4.27',
        'UE_4.26': '4.26',
    }

    return version_map.get(engine_association, engine_association)


def find_epic_manifests() -> List[Path]:
    """Find Epic Games Launcher manifest directories on the current platform.

    Returns:
        List of manifest directory paths
    """
    manifest_dirs = []

    if os.name == 'nt':  # Windows
        # ProgramData manifests
        program_data = Path(os.environ.get('PROGRAMDATA', 'C:\\ProgramData'))
        manifest_dirs.append(program_data / 'Epic' / 'UnrealEngineLauncher' / 'Manifest')

        # Local AppData manifests
        local_appdata = Path(os.environ.get('LOCALAPPDATA', ''))
        if local_appdata:
            manifest_dirs.append(local_appdata / 'EpicGamesLauncher' / 'Data' / 'Manifests')

    else:  # macOS/Linux
        home = Path.home()

        # macOS manifest locations
        manifest_dirs.extend([
            home / 'Library' / 'Application Support' / 'Epic' / 'UnrealEngineLauncher' / 'Manifest',
            home / 'Library' / 'Application Support' / 'Epic' / 'EpicGamesLauncher' / 'Data' / 'Manifests',
        ])

        # Linux manifest locations (if applicable)
        if os.name == 'posix' and os.uname().sysname == 'Linux':
            manifest_dirs.extend([
                home / '.local' / 'share' / 'Epic' / 'UnrealEngineLauncher' / 'Manifest',
                Path('/opt/Epic Games') / 'Launcher' / 'Manifests',
            ])

    return [d for d in manifest_dirs if d.exists() and d.is_dir()]


def parse_epic_manifests() -> Dict[str, Dict[str, Any]]:
    """Parse Epic Games Launcher manifests to extract engine installation info.

    Returns:
        Dictionary mapping engine identifiers to installation data
    """
    engines = {}

    for manifest_dir in find_epic_manifests():
        try:
            for manifest_file in manifest_dir.glob('*.item'):
                try:
                    with open(manifest_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    # Check if this is an engine manifest
                    if data.get('CatalogNamespace') == 'ue':
                        app_name = data.get('AppName', '')
                        install_location = data.get('InstallLocation', '')

                        if app_name and install_location:
                            engines[app_name] = {
                                'install_location': Path(install_location),
                                'display_name': data.get('DisplayName', ''),
                                'version': data.get('AppVersionString', ''),
                                'catalog_item_id': data.get('CatalogItemId', ''),
                            }

                except (json.JSONDecodeError, OSError) as e:
                    logger.warning(f"Failed to parse manifest {manifest_file}: {e}")
                    continue

        except OSError as e:
            logger.warning(f"Failed to read manifest directory {manifest_dir}: {e}")
            continue

    return engines


def resolve_engine_install_path(engine_version: str, manifests: Dict[str, Dict[str, Any]]) -> Optional[Path]:
    """Resolve the installation path for a given engine version.

    Args:
        engine_version: Engine version string (e.g., "5.3")
        manifests: Parsed manifest data from parse_epic_manifests()

    Returns:
        Path to engine installation or None if not found
    """
    if not engine_version:
        return None

    # Try direct version match
    for app_name, data in manifests.items():
        if data['version'] == engine_version:
            return data['install_location']

    # Try partial version match (e.g., "5.3" matches "5.3.0")
    for app_name, data in manifests.items():
        if data['version'].startswith(engine_version + '.'):
            return data['install_location']

    # Try catalog item ID patterns
    version_patterns = {
        '5.3': ['UE_5.3', 'UnrealEngine-5.3'],
        '5.2': ['UE_5.2', 'UnrealEngine-5.2'],
        '5.1': ['UE_5.1', 'UnrealEngine-5.1'],
        '5.0': ['UE_5.0', 'UnrealEngine-5.0'],
        '4.27': ['UE_4.27', 'UnrealEngine-4.27'],
    }

    patterns = version_patterns.get(engine_version, [])
    for pattern in patterns:
        for app_name, data in manifests.items():
            if pattern in app_name or pattern in data.get('catalog_item_id', ''):
                return data['install_location']

    return None


def discover_unreal_project(uproject_path: Path) -> UnrealProject:
    """Discover an Unreal Engine project from its .uproject file.

    Args:
        uproject_path: Path to the .uproject file

    Returns:
        UnrealProject instance with metadata and cache targets

    Raises:
        FileNotFoundError: If .uproject file doesn't exist
        ValueError: If .uproject parsing fails
    """
    metadata = parse_uproject_metadata(uproject_path)
    project_path = uproject_path.parent

    # Extract engine association
    engine_association = metadata.get('EngineAssociation')
    engine_version = resolve_engine_version(engine_association) if engine_association else None

    # Parse manifests to resolve engine path
    manifests = parse_epic_manifests()
    engine_path = resolve_engine_install_path(engine_version, manifests) if engine_version else None

    # Create cache targets
    caches = []

    # Project-level caches
    project_caches = [
        CacheTarget("DerivedDataCache", project_path / "DerivedDataCache", warn_on_delete=True,
                   description="Shader and derived data cache - rebuild required after deletion"),
        CacheTarget("Intermediate", project_path / "Intermediate", warn_on_delete=True,
                   description="Build intermediate files - rebuild required after deletion"),
        CacheTarget("Saved/Logs", project_path / "Saved" / "Logs",
                   description="Log files - safe to delete"),
        CacheTarget("Saved/Crashes", project_path / "Saved" / "Crashes",
                   description="Crash dumps - safe to delete"),
        CacheTarget("Binaries", project_path / "Binaries", warn_on_delete=True,
                   description="Compiled binaries - rebuild required after deletion"),
    ]

    for cache in project_caches:
        caches.append(cache)

    # Engine-level caches (if engine path is known)
    if engine_path:
        # Shader cache
        shader_cache = engine_path / "Engine" / "DerivedDataCache"
        if shader_cache.exists():
            caches.append(CacheTarget("Engine/ShaderCache", shader_cache, warn_on_delete=True,
                                    description="Engine shader cache - rebuild required after deletion"))

        # Marketplace assets (platform-specific)
        marketplace_paths = []
        if os.name == 'nt':  # Windows
            local_appdata = Path(os.environ.get('LOCALAPPDATA', ''))
            if local_appdata:
                marketplace_paths.append(local_appdata / 'EpicGamesLauncher' / 'Data' / 'Staged')
        else:  # macOS
            home = Path.home()
            marketplace_paths.extend([
                home / 'Library' / 'Application Support' / 'Epic' / 'EpicGamesLauncher' / 'Data' / 'Staged',
                home / 'Library' / 'Application Support' / 'EpicGamesLauncher' / 'Data' / 'Staged',
            ])

        for marketplace_path in marketplace_paths:
            if marketplace_path.exists():
                caches.append(CacheTarget("MarketplaceAssets", marketplace_path, requires_backup=True,
                                        description="Downloaded marketplace assets - backup recommended"))

    return UnrealProject(
        path=project_path,
        engine_version=engine_version,
        caches=caches,
        name=uproject_path.stem,
        uproject_file=uproject_path
    )