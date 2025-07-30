"""Unity Hub project parser module.

This module provides functionality to read and parse Unity Hub's projects
configuration file to extract project information.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any


def read_unity_hub_projects(json_path: str = None) -> List[Dict[str, str]]:
    """Read Unity Hub projects from the projects JSON file.
    
    Args:
        json_path: Optional path to the Unity Hub projects JSON file.
                  If not provided, uses the default location:
                  ~/Library/Application Support/UnityHub/projects-v1.json
    
    Returns:
        List of dictionaries containing project information with keys:
        - 'name': The project name
        - 'path': The project path
        Returns empty list if file is missing or malformed.
    """

    if json_path is None:
        # Use default Unity Hub projects file location on macOS
        home = Path.home()
        json_path = home / "Library" / "Application Support" / "UnityHub" / "projects-v1.json"
    else:
        json_path = Path(json_path)

    # Return empty list if file doesn't exist
    if not json_path.exists():
        return []

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Unity Hub stores projects in a dictionary where keys are paths
        # and values contain project metadata
        projects = []

        # Handle new Unity Hub format with schema_version and data fields
        if isinstance(data, dict) and 'schema_version' in data and 'data' in data:
            # New format: {"schema_version": "v1", "data": {...}}
            projects_data = data.get('data', {})
        else:
            # Old format: direct dictionary of projects
            projects_data = data

        if isinstance(projects_data, dict):
            for project_path, project_info in projects_data.items():
                # Validate that the key looks like a file path
                # Unity Hub uses absolute paths as keys
                if not (project_path.startswith('/') or 
                        (len(project_path) > 2 and project_path[1:3] == ':\\') or
                        (len(project_path) > 2 and project_path[1:3] == ':/')):  # Windows paths
                    continue
                    
                project_name = os.path.basename(project_path)

                if isinstance(project_info, dict):
                    # Try 'title' first (new format), then 'name' (old format), then use basename
                    project_name = project_info.get('title', project_info.get('name', project_name))

                projects.append({
                    'name': project_name,
                    'path': project_path
                })

        return projects

    except (json.JSONDecodeError, KeyError, TypeError):
        return []
    except Exception:
        return []







