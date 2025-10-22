import json

import pytest

from helpers.unreal_launcher import (
    find_projects_in_paths,
    read_unreal_launcher_projects,
)


@pytest.fixture
def create_mock_manifest_dir(tmp_path):
    """Create a mock manifest directory with test files."""
    manifest_dir = tmp_path / "Manifest"
    manifest_dir.mkdir()

    # Create mock manifest files
    project1 = {
        "DisplayName": "TestProject1",
        "InstallLocation": str(tmp_path / "TestProject1"),
    }
    project2 = {
        "DisplayName": "TestProject2",
        "InstallLocation": str(tmp_path / "TestProject2"),
    }

    with open(manifest_dir / "project1.item", "w") as f:
        json.dump(project1, f)
    with open(manifest_dir / "project2.item", "w") as f:
        json.dump(project2, f)

    return manifest_dir


# Test reading from launcher project manifest


def test_read_unreal_launcher_projects(create_mock_manifest_dir):
    manifest_dir = create_mock_manifest_dir
    projects = read_unreal_launcher_projects(str(manifest_dir))
    assert len(projects) == 2

    assert projects[0]["name"] == "TestProject1"
    assert "TestProject1" in projects[0]["path"]


# Test finding projects in non-default paths
def test_find_projects_in_paths(tmp_path):
    project_path = tmp_path / "CustomUnrealProject"
    project_path.mkdir()
    uproject_file = project_path / "CustomProject.uproject"
    uproject_file.touch()

    paths = [tmp_path]
    projects = find_projects_in_paths(paths)
    assert len(projects) == 1
    assert projects[0]["name"] == "CustomProject"


# Test getting unreal projects from multiple sources
def test_get_unreal_projects(create_mock_manifest_dir, tmp_path):
    project_path = tmp_path / "AnotherUnrealProject"
    project_path.mkdir()
    uproject_file = project_path / "AnotherProject.uproject"
    uproject_file.touch()

    # Mock non-default paths
    custom_paths = [project_path]

    # Combine projects
    manifest_projects = read_unreal_launcher_projects(str(create_mock_manifest_dir))
    path_projects = find_projects_in_paths(custom_paths)
    all_projects = manifest_projects + path_projects

    assert len(all_projects) == 3

    # Check all project names are in results
    project_names = {p["name"] for p in all_projects}
    assert "TestProject1" in project_names
    assert "TestProject2" in project_names
    assert "AnotherProject" in project_names


# Test edge case for non-existent manifest directory
def test_read_unreal_launcher_projects_no_dir():
    projects = read_unreal_launcher_projects("/non/existent/path")
    assert projects == []
