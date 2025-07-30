# Unity Hub Parser Module

## Overview

The `unity_hub.py` module provides functionality to read and parse Unity Hub's project configuration file (`projects-v1.json`) to extract project information.

## Features

- Reads Unity Hub's default project configuration file on macOS
- Supports custom file paths for cross-platform compatibility
- Handles malformed or missing JSON files gracefully
- Validates project paths to ensure correct Unity Hub format
- Supports Unicode characters in project names and paths

## Usage

### Basic Usage

```python
from helpers.unity_hub import read_unity_hub_projects

# Read from default Unity Hub location
projects = read_unity_hub_projects()

# Process the results
for project in projects:
    print(f"Project: {project['name']}")
    print(f"Path: {project['path']}")
```

### Custom File Path

```python
# Read from a custom location
projects = read_unity_hub_projects("/path/to/projects-v1.json")
```

## Function Reference

### `read_unity_hub_projects(json_path=None)`

Reads Unity Hub projects from the projects JSON file.

**Parameters:**
- `json_path` (str, optional): Path to the Unity Hub projects JSON file. If not provided, uses the default location: `~/Library/Application Support/UnityHub/projects-v1.json`

**Returns:**
- List[Dict[str, str]]: A list of dictionaries, each containing:
  - `'name'`: The project name
  - `'path'`: The absolute path to the project

**Behavior:**
- Returns an empty list if:
  - The file doesn't exist
  - The JSON is malformed
  - The JSON structure doesn't match Unity Hub's format
- Validates that dictionary keys are valid file paths (absolute paths)
- Extracts project names from metadata if available, otherwise uses the directory name

## Unity Hub JSON Format

Unity Hub stores projects in a JSON file with the following structure:

```json
{
  "/path/to/project1": {
    "name": "Project Name",
    "version": "2022.3.10f1",
    "lastOpened": 1234567890
  },
  "/path/to/project2": {
    "version": "2021.3.15f1"
  }
}
```

The module handles variations in this structure, including:
- Projects with or without a "name" field
- Projects with minimal or no metadata
- Unicode characters in paths and names

## Testing

The module includes comprehensive unit tests in `tests/test_unity_hub.py`. Run tests with:

```bash
python -m unittest tests.test_unity_hub -v
```

## Example

See `examples/unity_hub_example.py` for a complete example of using the module.
