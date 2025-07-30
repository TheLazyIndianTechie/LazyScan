import os


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
        "Library": os.path.join(project_path, 'Library'),
        "Temp": os.path.join(project_path, 'Temp'),
        "obj": os.path.join(project_path, 'obj'),
        "Logs": os.path.join(project_path, 'Logs'),
    }
    if include_build:
        cache_targets["Build"] = os.path.join(project_path, 'Build')
    return cache_targets


def generate_unity_project_report(project_path, project_name=None, include_build=False):
    """Generates a detailed cache report for a Unity project."""
    if not project_name:
        project_name = os.path.basename(project_path)

    cache_dirs = {}
    total_size = 0

    cache_targets = get_unity_cache_targets(project_path, include_build=include_build)

    for cache_name, cache_path in cache_targets.items():
        size = 0
        exists = os.path.exists(cache_path)
        if exists:
            size = compute_directory_size(cache_path)
            total_size += size
        cache_dirs[cache_name] = {"exists": exists, "size": size, "path": cache_path}

    build_dir_size = 0
    if "Build" in cache_targets and os.path.exists(cache_targets["Build"]):
        build_dir_size = compute_directory_size(cache_targets["Build"])

    return {
        "name": project_name,
        "path": project_path,
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
