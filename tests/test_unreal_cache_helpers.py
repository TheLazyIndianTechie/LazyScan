import pytest
import os
from helpers.unreal_cache_helpers import (
    generate_unreal_project_report,
    scan_unreal_project,
)


@pytest.fixture
def create_mock_unreal_project(tmp_path):
    """Create a mock Unreal Engine project with necessary directories"""
    project_path = tmp_path / "MockUnrealProject"
    project_path.mkdir()

    # Create cache directories with dummy files
    intermediate_dir = project_path / "Intermediate"
    intermediate_dir.mkdir()
    (intermediate_dir / "dummy1.tmp").write_bytes(b"x" * 1024)  # 1KB

    saved_logs_dir = project_path / "Saved/Logs"
    saved_logs_dir.mkdir(parents=True)
    (saved_logs_dir / "log.txt").write_bytes(b"x" * 512)  # 0.5KB

    return project_path


# Test cache size calculation


def test_cache_size_calculation(create_mock_unreal_project):
    project_path = create_mock_unreal_project

    report = generate_unreal_project_report(str(project_path), "MockUnrealProject")
    assert report["total_size"] == 1024 + 512


# Test project report generation


def test_project_report_generation_with_missing_dirs(tmp_path):
    project_path = tmp_path / "MissingDirsProject"
    project_path.mkdir()

    report = generate_unreal_project_report(str(project_path), "MissingDirsProject")
    # All directories should not exist
    for cache_directory in report["cache_dirs"].values():
        assert cache_directory["exists"] is False
        assert cache_directory["size"] == 0


# Test edge case with permission error


def test_generate_unreal_project_report_permission_error(tmp_path):
    project_path = tmp_path / "PermissionErrorProject"
    project_path.mkdir()
    os.chmod(project_path, 0o000)  # No permissions

    try:
        report = scan_unreal_project(str(project_path))
    except PermissionError:
        report = {}

    assert report == {}

    # Restore permissions for cleanup
    os.chmod(project_path, 0o755)
