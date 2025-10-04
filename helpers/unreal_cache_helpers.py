import os
import json
from pathlib import Path
from .unity_cache_helpers import compute_directory_size


def discover_uproject_files(directory):
    """
    Discovers all .uproject files in the specified directory and its subdirectories.

    Args:
        directory: The root directory to search for .uproject files.

    Returns:
        A list of paths to .uproject files.
    """
    uproject_files = []

    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".uproject"):
                full_path = os.path.join(root, file)
                uproject_files.append(full_path)

    return uproject_files


def get_unreal_cache_targets(project_path, engine_version=None):
    """
    Returns a dictionary of cache target directories for an Unreal Engine project.

    Args:
        project_path: Path to the Unreal Engine project directory.
        engine_version: Optional engine version for additional engine-level caches.

    Returns:
        Dictionary mapping cache directory names to their paths.
    """
    cache_targets = {
        # Project-level caches
        "DerivedDataCache": os.path.join(project_path, "DerivedDataCache"),
        "Intermediate": os.path.join(project_path, "Intermediate"),
        "Saved/Logs": os.path.join(project_path, "Saved", "Logs"),
        "Saved/Crashes": os.path.join(project_path, "Saved", "Crashes"),
        "Binaries": os.path.join(project_path, "Binaries"),
        "Saved/Backup": os.path.join(project_path, "Saved", "Backup"),
        "Plugins/Intermediate": os.path.join(project_path, "Plugins", "Intermediate"),
        "Plugins/Binaries": os.path.join(project_path, "Plugins", "Binaries"),
    }

    # Note: Engine-specific caches will be added when integrating with unreal_version module
    # For now, we focus on project-level caches

    # Add platform-specific marketplace caches
    if os.name == 'nt':  # Windows
        local_appdata = os.environ.get('LOCALAPPDATA', '')
        if local_appdata:
            cache_targets.update({
                "MarketplaceAssets": os.path.join(local_appdata, 'EpicGamesLauncher', 'Data', 'Staged'),
                "LauncherCache": os.path.join(local_appdata, 'EpicGamesLauncher', 'Data', 'Cache'),
            })
    else:  # macOS/Linux
        home = os.path.expanduser('~')
        cache_targets.update({
            "MarketplaceAssets": os.path.join(home, 'Library', 'Application Support', 'Epic', 'EpicGamesLauncher', 'Data', 'Staged'),
            "LauncherCache": os.path.join(home, 'Library', 'Application Support', 'Epic', 'EpicGamesLauncher', 'Data', 'Cache'),
        })

    return cache_targets


def parse_uproject_metadata(uproject_path):
    """
    Parse .uproject file and extract metadata including EngineAssociation.

    Args:
        uproject_path: Path to the .uproject file

    Returns:
        Dictionary containing project metadata, or None if parsing fails
    """
    try:
        with open(uproject_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        if not isinstance(metadata, dict):
            return None

        return metadata
    except (json.JSONDecodeError, OSError):
        return None


def resolve_engine_version(engine_association):
    """
    Resolve engine version from EngineAssociation string.

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


def generate_unreal_project_report(project_path, project_name=None):
    """
    Generates a detailed cache report for an Unreal Engine project.

    Args:
        project_path: Path to the Unreal Engine project directory.
        project_name: Optional project name. If not provided, uses the directory name.

    Returns:
        Dictionary containing:
        - name: Project name
        - path: Project path
        - uproject_file: Path to the .uproject file (if found)
        - engine_version: Resolved engine version (if available)
        - cache_dirs: Dictionary of cache directories with their existence status and sizes
        - total_size: Total size of all cache directories
    """
    if not project_name:
        project_name = os.path.basename(project_path)

    # Find the .uproject file in the project directory
    uproject_file = None
    engine_version = None

    for file in os.listdir(project_path):
        if file.endswith(".uproject"):
            uproject_file = os.path.join(project_path, file)
            # Use the .uproject filename (without extension) as project name if not specified
            if not project_name or project_name == os.path.basename(project_path):
                project_name = os.path.splitext(file)[0]

            # Try to parse engine version
            metadata = parse_uproject_metadata(uproject_file)
            if metadata:
                engine_association = metadata.get('EngineAssociation')
                if engine_association:
                    engine_version = resolve_engine_version(engine_association)
            break

    cache_dirs = {}
    total_size = 0

    cache_targets = get_unreal_cache_targets(project_path, engine_version)

    # Define cache categories with their properties
    cache_metadata = {
        # Critical caches that require rebuild
        "DerivedDataCache": {
            "warn_on_delete": True,
            "requires_backup": True,
            "description": "Shader and derived data cache - rebuild required after deletion",
            "category": "build"
        },
        "Intermediate": {
            "warn_on_delete": True,
            "requires_backup": False,
            "description": "Build intermediate files - rebuild required after deletion",
            "category": "build"
        },
        "Binaries": {
            "warn_on_delete": True,
            "requires_backup": False,
            "description": "Compiled binaries - rebuild required after deletion",
            "category": "build"
        },
        "Engine/DerivedDataCache": {
            "warn_on_delete": True,
            "requires_backup": True,
            "description": "Engine shader cache - affects all projects using this engine",
            "category": "engine"
        },
        "Engine/Intermediate": {
            "warn_on_delete": True,
            "requires_backup": False,
            "description": "Engine build intermediates - rebuild required after deletion",
            "category": "engine"
        },
        "Plugins/Intermediate": {
            "warn_on_delete": True,
            "requires_backup": False,
            "description": "Plugin build intermediates - rebuild required after deletion",
            "category": "build"
        },
        "Plugins/Binaries": {
            "warn_on_delete": True,
            "requires_backup": False,
            "description": "Plugin binaries - rebuild required after deletion",
            "category": "build"
        },

        # Safe to delete caches
        "Saved/Logs": {
            "warn_on_delete": False,
            "requires_backup": False,
            "description": "Log files - safe to delete",
            "category": "logs"
        },
        "Saved/Crashes": {
            "warn_on_delete": False,
            "requires_backup": False,
            "description": "Crash dumps - safe to delete",
            "category": "logs"
        },
        "Saved/Backup": {
            "warn_on_delete": False,
            "requires_backup": False,
            "description": "Backup files - safe to delete",
            "category": "temp"
        },

        # Marketplace and launcher caches
        "MarketplaceAssets": {
            "warn_on_delete": False,
            "requires_backup": True,
            "description": "Downloaded marketplace assets - backup recommended before deletion",
            "category": "marketplace"
        },
        "LauncherCache": {
            "warn_on_delete": False,
            "requires_backup": False,
            "description": "Epic Games Launcher cache - safe to delete",
            "category": "launcher"
        },
    }

    for cache_name, cache_path in cache_targets.items():
        size = 0
        exists = os.path.exists(cache_path)
        if exists:
            size = compute_directory_size(cache_path)
            total_size += size

        # Get metadata for this cache type
        metadata = cache_metadata.get(cache_name, {
            "warn_on_delete": False,
            "requires_backup": False,
            "description": f"Cache directory: {cache_name}",
            "category": "unknown"
        })

        cache_dirs[cache_name] = {
            "exists": exists,
            "size": size,
            "path": cache_path,
            "warn_on_delete": metadata["warn_on_delete"],
            "requires_backup": metadata["requires_backup"],
            "description": metadata["description"],
            "category": metadata["category"]
        }

    return {
        "name": project_name,
        "path": project_path,
        "uproject_file": uproject_file,
        "engine_version": engine_version,
        "cache_dirs": cache_dirs,
        "total_size": total_size,
    }


def scan_unreal_project(project_path):
    """
    Scans an Unreal Engine project to generate a report of its cache directories.

    This is a cleaner interface for scanning Unreal projects that can be reused
    in both picker and manual modes.

    Args:
        project_path: Path to the Unreal Engine project.

    Returns:
        A dictionary containing the project's report.
    """
    return generate_unreal_project_report(project_path)


def find_unreal_projects_in_directory(directory):
    """
    Finds all Unreal Engine projects in a directory by looking for .uproject files.

    Args:
        directory: The directory to search for Unreal projects.

    Returns:
        A list of project paths (directories containing .uproject files).
    """
    uproject_files = discover_uproject_files(directory)

    # Get unique project directories
    project_dirs = set()
    for uproject_file in uproject_files:
        project_dir = os.path.dirname(uproject_file)
        project_dirs.add(project_dir)

    return sorted(list(project_dirs))
