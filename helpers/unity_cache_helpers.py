import os
from pathlib import Path
from typing import Optional

# Import version detection functionality
parse_project_version = None
get_unity_cache_paths = None
UnityVersion = None

try:
    import sys
    import os
    # Try to import from the same directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    from unity_version import parse_project_version, get_unity_cache_paths, UnityVersion
except ImportError:
    # Fallback for when the module is not available yet
    pass


def compute_directory_size(path):
    """Recursively calculates the total file size of a directory."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.exists(fp):
                total_size += os.path.getsize(fp)
    return total_size


def get_unity_cache_targets(project_path, include_build=False):
    """Returns a dictionary of cache target directories for a Unity project."""
    cache_targets = {
        "Library": os.path.join(project_path, "Library"),
        "Temp": os.path.join(project_path, "Temp"),
        "obj": os.path.join(project_path, "obj"),
        "Logs": os.path.join(project_path, "Logs"),
    }
    if include_build:
        cache_targets["Build"] = os.path.join(project_path, "Build")
    return cache_targets


def generate_unity_project_report(project_path, project_name=None, include_build=False, include_global_cache=True):
    """Generates a detailed cache report for a Unity project."""
    from lazyscan.core.config import get_typed_config

    project_path = Path(project_path)
    if not project_name:
        project_name = project_path.name

    # Get configuration
    config = get_typed_config()
    version_aware_cache = getattr(config.unity, 'version_aware_cache', True)
    include_global = include_global_cache and getattr(config.unity, 'include_global_cache', True)

    # Try to import version detection functionality
    unity_version = None
    global_cache_paths = {}

    try:
        import sys
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)

        from unity_version import parse_project_version, get_unity_cache_paths
        unity_version = parse_project_version(project_path)
        if unity_version and include_global and version_aware_cache:
            global_cache_paths = get_unity_cache_paths(unity_version)
    except ImportError:
        # Version detection not available, continue with basic functionality
        pass

    cache_dirs = {}
    total_size = 0

    # Get project-local cache targets
    cache_targets = get_unity_cache_targets(str(project_path), include_build=include_build)

    for cache_name, cache_path in cache_targets.items():
        size = 0
        exists = os.path.exists(cache_path)
        if exists:
            size = compute_directory_size(cache_path)
            total_size += size
        cache_dirs[cache_name] = {"exists": exists, "size": size, "path": cache_path}

    # Add global Unity cache directories if available
    for cache_type, cache_path in global_cache_paths.items():
        size = 0
        exists = os.path.exists(cache_path)
        if exists:
            size = compute_directory_size(cache_path)
            total_size += size
        cache_dirs[cache_type] = {"exists": exists, "size": size, "path": cache_path}

    build_dir_size = 0
    if "Build" in cache_targets and os.path.exists(cache_targets["Build"]):
        build_dir_size = compute_directory_size(cache_targets["Build"])

    return {
        "name": project_name,
        "path": str(project_path),
        "unity_version": str(unity_version) if unity_version else None,
        "cache_dirs": cache_dirs,
        "total_size": total_size,
        "has_build_dir": "Build" in cache_targets,
        "build_dir_size": build_dir_size,
    }


def scan_unity_project(project_path, include_build=False):
    """
    Scans a Unity project to generate a report of its cache and optionally build directory.

    This is a cleaner interface for scanning Unity projects that can be reused
    in both picker and manual modes.

    Args:
        project_path: Path to the Unity project.
        include_build: Boolean indicating whether to include the build directory size.

    Returns:
        A dictionary containing the project's report.
    """
    return generate_unity_project_report(project_path, include_build=include_build)
