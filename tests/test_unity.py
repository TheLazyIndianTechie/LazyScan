import pytest
import json
import pytest
from unittest import mock
from pathlib import Path
from lazyscan.apps.unity import (
    scan_unity_project_via_hub,
    prompt_unity_project_selection,
    _get_cache_impact_description,
)


@pytest.fixture
def create_mock_unity_hub_json(tmp_path):
    # Create a mock Unity Hub JSON file
    projects_data = {
        "recentProjects": [
            {"name": "TestProject1", "path": str(tmp_path / "TestProject1")},
            {"name": "TestProject2", "path": str(tmp_path / "TestProject2")},
        ]
    }
    json_path = tmp_path / "mock_unity_hub.json"
    with open(json_path, "w") as f:
        json.dump(projects_data, f)
    return json_path


@mock.patch("lazyscan.apps.unity.read_unity_hub_projects")
def test_scan_unity_project_via_hub(mock_read_projects, create_mock_unity_hub_json):
    mock_read_projects.return_value = [
        {"name": "TestProject1", "path": "dummy/TestProject1"},
        {"name": "TestProject2", "path": "dummy/TestProject2"},
    ]

    args = mock.Mock()
    args.unityhub_json = create_mock_unity_hub_json

    scan_unity_project_via_hub(args, clean=True)

    assert mock_read_projects.called


@mock.patch("sys.stdin.isatty", return_value=True)  # Mock interactive terminal
@mock.patch("builtins.input", return_value="1")
def test_prompt_unity_project_selection(mock_input, mock_isatty):
    projects = [
        {"name": "TestProject1", "path": "dummy/TestProject1"},
        {"name": "TestProject2", "path": "dummy/TestProject2"},
    ]

    selected = prompt_unity_project_selection(projects)

    assert len(selected) == 1
    assert selected[0]["name"] == "TestProject1"


class TestCacheImpactDescription:
    """Test cache impact description functionality."""

    def test_library_impact_high(self):
        """Test Library impact for large sizes."""
        impact = _get_cache_impact_description("Library", 6 * 1024 * 1024 * 1024)  # 6GB
        assert "Very high" in impact
        assert "rebuild required" in impact

    def test_library_impact_medium(self):
        """Test Library impact for medium sizes."""
        impact = _get_cache_impact_description("Library", 1024 * 1024 * 1024)  # 1GB
        assert "High" in impact
        assert "rebuild time" in impact

    def test_build_impact_high(self):
        """Test Build directory impact for large sizes."""
        impact = _get_cache_impact_description("Build", 15 * 1024 * 1024 * 1024)  # 15GB
        assert "Very high" in impact
        assert "build time" in impact

    def test_temp_impact(self):
        """Test Temp directory impact."""
        impact = _get_cache_impact_description("Temp", 100 * 1024 * 1024)  # 100MB
        assert "Low" in impact
        assert "regeneration" in impact

    def test_logs_impact(self):
        """Test Logs directory impact."""
        impact = _get_cache_impact_description("Logs", 50 * 1024 * 1024)  # 50MB
        assert "None" in impact
        assert "safe to clean" in impact

    def test_package_cache_impact(self):
        """Test package cache impact."""
        impact = _get_cache_impact_description("package_cache", 500 * 1024 * 1024)  # 500MB
        assert "Medium" in impact
        assert "download required" in impact

    def test_unknown_cache_impact(self):
        """Test unknown cache type impact."""
        impact = _get_cache_impact_description("unknown_cache", 100 * 1024 * 1024)  # 100MB
        assert "Unknown impact" in impact


class TestUnityVersionIntegration:
    """Test Unity version integration in cache helpers."""

    def test_generate_unity_project_report_with_version(self, tmp_path):
        """Test that generate_unity_project_report includes version information."""
        from helpers.unity_cache_helpers import generate_unity_project_report

        # Create a mock Unity project with version file
        project_dir = tmp_path / "TestUnityProject"
        project_dir.mkdir()
        settings_dir = project_dir / "ProjectSettings"
        settings_dir.mkdir()

        # Create ProjectVersion.txt
        version_file = settings_dir / "ProjectVersion.txt"
        version_file.write_text("m_EditorVersion: 2021.3.15f1\n")

        # Create some cache directories
        library_dir = project_dir / "Library"
        library_dir.mkdir()
        (library_dir / "test_file.txt").write_text("test")

        temp_dir = project_dir / "Temp"
        temp_dir.mkdir()
        (temp_dir / "temp_file.txt").write_text("temp")

        report = generate_unity_project_report(str(project_dir))

        # Check that version is detected
        assert report["unity_version"] == "2021.3.15f1"
        assert "Library" in report["cache_dirs"]
        assert "Temp" in report["cache_dirs"]

    def test_generate_unity_project_report_without_version(self, tmp_path):
        """Test report generation when version detection fails."""
        from helpers.unity_cache_helpers import generate_unity_project_report

        # Create a project without version file
        project_dir = tmp_path / "TestUnityProject"
        project_dir.mkdir()

        library_dir = project_dir / "Library"
        library_dir.mkdir()

        report = generate_unity_project_report(str(project_dir))

        # Version should be None
        assert report["unity_version"] is None
        assert "Library" in report["cache_dirs"]

    @mock.patch('lazyscan.core.config.get_typed_config')
    def test_generate_unity_project_report_with_global_cache(self, mock_config, tmp_path):
        """Test report generation with global cache enabled."""
        from helpers.unity_cache_helpers import generate_unity_project_report
        from lazyscan.core.config import UnityConfig

        # Mock config to enable global cache
        mock_unity_config = UnityConfig(include_global_cache=True, version_aware_cache=True)
        mock_config.return_value = mock.Mock(unity=mock_unity_config)

        # Create a mock Unity project
        project_dir = tmp_path / "TestUnityProject"
        project_dir.mkdir()
        settings_dir = project_dir / "ProjectSettings"
        settings_dir.mkdir()

        version_file = settings_dir / "ProjectVersion.txt"
        version_file.write_text("m_EditorVersion: 2021.3.15f1\n")

        report = generate_unity_project_report(str(project_dir), include_global_cache=True)

        # Should include global cache directories if version detection works
        # (This will depend on whether the unity_version module is available)
        assert "unity_version" in report
        assert isinstance(report["cache_dirs"], dict)
