"""Unreal Launcher project parser module.

This module provides functionality to read and parse Epic Games Launcher's project
manifest files to extract project information.
"""

import json
import os
from pathlib import Path


def read_unreal_launcher_projects(manifest_dir: str = None) -> list[dict[str, str]]:
    """Read registered Unreal Engine projects from manifest files.

    Args:
        manifest_dir: Optional directory path containing the manifest files.
                      On macOS: ~/Library/Application Support/Epic/UnrealEngineLauncher/Manifest
                      On Windows: C:/ProgramData/Epic/UnrealEngineLauncher/Manifest

    Returns:
        List of dictionaries containing project information with keys:
        - 'name': The project name
        - 'path': The project path
        Returns empty list if files are missing or malformed.
    """

    if manifest_dir is None:
        # Default launcher manifest locations
        if os.name == "nt":  # Windows
            manifest_dir = Path("C:/ProgramData/Epic/UnrealEngineLauncher/Manifest")
        else:  # macOS
            home = Path.home()
            # Try both old and new manifest locations
            manifest_dir = None
            possible_paths = [
                home / "Library/Application Support/Epic/UnrealEngineLauncher/Manifest",
                home
                / "Library/Application Support/Epic/EpicGamesLauncher/Data/Manifests",
            ]
            for path in possible_paths:
                if path.exists() and path.is_dir():
                    manifest_dir = path
                    break

            # If no manifest directory found, default to the first one
            if manifest_dir is None:
                manifest_dir = possible_paths[0]
    else:
        manifest_dir = Path(manifest_dir)

    projects = []

    if not manifest_dir.exists() or not manifest_dir.is_dir():
        return projects

    try:
        for manifest_file in manifest_dir.glob("*.item"):
            try:
                with open(manifest_file, encoding="utf-8") as f:
                    data = json.load(f)
                    # Check install location first
                    install_path = Path(data.get("InstallLocation", ""))
                    if not install_path.exists():
                        continue

                    # Search for .uproject files in the install location
                    for uproject in install_path.rglob("*.uproject"):
                        project_name = uproject.stem
                        project_path = uproject.parent
                        if project_path.exists():
                            projects.append(
                                {"name": project_name, "path": str(project_path)}
                            )
            except Exception as e:
                print(f"Error reading manifest {manifest_file}: {e}")

    except (json.JSONDecodeError, KeyError, TypeError, OSError):
        return projects

    return projects


def find_projects_in_paths(paths: list[Path]) -> list[dict[str, str]]:
    """Search specified paths for Unreal Engine projects.

    Args:
        paths: List of paths to scan for user projects.

    Returns:
        List of dictionaries containing project information with keys:
        - 'name': The project name
        - 'path': The project path
        Returns empty list if no projects found.
    """
    projects = []

    def is_user_project(path: Path) -> bool:
        """Check if a .uproject file belongs to a user project."""
        path_str = str(path).lower()
        # Exclude common non-user project paths
        excluded_patterns = [
            "engine/programs",
            "engine/source",
            "/templates/",
            "enginetest",
            "testproject",
            "/samples/",
            "/content/examples/",
            "tp_",  # Template projects
        ]
        return not any(pattern in path_str.lower() for pattern in excluded_patterns)

    for path in paths:
        if not path.exists():
            continue

        # Look for .uproject files recursively
        for project_file in path.rglob("*.uproject"):
            if is_user_project(project_file):
                project_name = project_file.stem
                projects.append(
                    {"name": project_name, "path": str(project_file.parent)}
                )

    return projects


def get_unreal_projects() -> list[dict[str, str]]:
    """Find Unreal Engine user projects in common locations.

    Returns:
        List of project information with each entry having:
        - 'name': The project name
        - 'path': The project path
    """
    # Common locations for user projects
    home = Path.home()
    search_paths = [
        home / "Documents/Unreal Projects",  # Default location
        home / "UnrealProjects",  # Common alternative
        home / "Documents/UnrealProjects",  # Another common location
        home / "Projects/Unreal",  # Developer-style organization
        Path("/Volumes"),  # External drives on macOS
    ]

    # Add any currently open project from launcher manifests
    manifest_projects = read_unreal_launcher_projects()
    # Filter out non-user projects from manifests
    manifest_projects = [
        p
        for p in manifest_projects
        if not any(
            pattern in str(p["path"]).lower()
            for pattern in ["engine/programs", "engine/source", "/templates/", "tp_"]
        )
    ]

    # Find additional projects in search paths
    path_projects = find_projects_in_paths(search_paths)

    # Combine and remove duplicates
    all_projects = manifest_projects + path_projects
    unique_projects = []
    seen_paths = set()

    for project in all_projects:
        if project["path"] not in seen_paths:
            seen_paths.add(project["path"])
            unique_projects.append(project)

    return unique_projects
