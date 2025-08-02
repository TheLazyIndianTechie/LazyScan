import os
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
            if file.endswith('.uproject'):
                full_path = os.path.join(root, file)
                uproject_files.append(full_path)
    
    return uproject_files


def get_unreal_cache_targets(project_path):
    """
    Returns a dictionary of cache target directories for an Unreal Engine project.
    
    Args:
        project_path: Path to the Unreal Engine project directory.
    
    Returns:
        Dictionary mapping cache directory names to their paths.
    """
    cache_targets = {
        "Intermediate": os.path.join(project_path, 'Intermediate'),
        "Saved/Logs": os.path.join(project_path, 'Saved', 'Logs'),
        "Saved/Crashes": os.path.join(project_path, 'Saved', 'Crashes'),
        "DerivedDataCache": os.path.join(project_path, 'DerivedDataCache'),
        "Binaries": os.path.join(project_path, 'Binaries'),
    }
    return cache_targets


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
        - cache_dirs: Dictionary of cache directories with their existence status and sizes
        - total_size: Total size of all cache directories
    """
    if not project_name:
        project_name = os.path.basename(project_path)
    
    # Find the .uproject file in the project directory
    uproject_file = None
    for file in os.listdir(project_path):
        if file.endswith('.uproject'):
            uproject_file = os.path.join(project_path, file)
            # Use the .uproject filename (without extension) as project name if not specified
            if not project_name or project_name == os.path.basename(project_path):
                project_name = os.path.splitext(file)[0]
            break
    
    cache_dirs = {}
    total_size = 0
    
    cache_targets = get_unreal_cache_targets(project_path)
    
    for cache_name, cache_path in cache_targets.items():
        size = 0
        exists = os.path.exists(cache_path)
        if exists:
            size = compute_directory_size(cache_path)
            total_size += size
        cache_dirs[cache_name] = {
            "exists": exists,
            "size": size,
            "path": cache_path
        }
    
    return {
        "name": project_name,
        "path": project_path,
        "uproject_file": uproject_file,
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
