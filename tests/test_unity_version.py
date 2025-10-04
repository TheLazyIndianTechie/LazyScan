"""Tests for Unity version detection and management functionality."""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, mock_open

# Import the module to test
try:
    import sys
    import os
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

    from helpers.unity_version import (
        parse_project_version,
        get_unity_installations,
        find_matching_unity_installation,
        get_unity_cache_paths,
        UnityVersion,
    )
except ImportError:
    pytest.skip("unity_version module not available", allow_module_level=True)


class TestUnityVersion:
    """Test UnityVersion dataclass functionality."""

    def test_version_creation(self):
        """Test creating UnityVersion instances."""
        version = UnityVersion(major=2021, minor=3, patch=15, revision="f1", full_version="2021.3.15f1")
        assert version.major == 2021
        assert version.minor == 3
        assert version.patch == 15
        assert version.revision == "f1"
        assert str(version) == "2021.3.15f1"

    def test_version_comparison(self):
        """Test version comparison."""
        v1 = UnityVersion(major=2021, minor=3, patch=15)
        v2 = UnityVersion(major=2021, minor=3, patch=16)
        v3 = UnityVersion(major=2022, minor=1, patch=0)

        assert v1 < v2
        assert v2 < v3
        assert v1 < v3

    def test_version_equality(self):
        """Test version equality."""
        v1 = UnityVersion(major=2021, minor=3, patch=15, revision="f1")
        v2 = UnityVersion(major=2021, minor=3, patch=15, revision="f1")
        v3 = UnityVersion(major=2021, minor=3, patch=15, revision="f2")

        assert v1 == v2
        assert v1 != v3


class TestParseProjectVersion:
    """Test parsing Unity project versions."""

    def test_parse_valid_version_file(self, tmp_path):
        """Test parsing a valid ProjectVersion.txt file."""
        project_dir = tmp_path / "TestProject"
        project_dir.mkdir()
        settings_dir = project_dir / "ProjectSettings"
        settings_dir.mkdir()

        version_file = settings_dir / "ProjectVersion.txt"
        version_file.write_text("m_EditorVersion: 2021.3.15f1\nm_EditorVersionWithRevision: 2021.3.15f1 (b3b2c6512324)\n")

        version = parse_project_version(project_dir)
        assert version is not None
        assert version.major == 2021
        assert version.minor == 3
        assert version.patch == 15
        assert version.revision == "f1"
        assert version.full_version == "2021.3.15f1"

    def test_parse_version_without_revision(self, tmp_path):
        """Test parsing version without revision suffix."""
        project_dir = tmp_path / "TestProject"
        project_dir.mkdir()
        settings_dir = project_dir / "ProjectSettings"
        settings_dir.mkdir()

        version_file = settings_dir / "ProjectVersion.txt"
        version_file.write_text("m_EditorVersion: 2022.2.0\n")

        version = parse_project_version(project_dir)
        assert version is not None
        assert version.major == 2022
        assert version.minor == 2
        assert version.patch == 0
        assert version.revision is None
        assert version.full_version == "2022.2.0"

    def test_parse_missing_version_file(self, tmp_path):
        """Test handling missing ProjectVersion.txt file."""
        project_dir = tmp_path / "TestProject"
        project_dir.mkdir()

        version = parse_project_version(project_dir)
        assert version is None

    def test_parse_missing_project_settings(self, tmp_path):
        """Test handling missing ProjectSettings directory."""
        project_dir = tmp_path / "TestProject"
        project_dir.mkdir()

        version = parse_project_version(project_dir)
        assert version is None

    def test_parse_malformed_version(self, tmp_path):
        """Test handling malformed version strings."""
        project_dir = tmp_path / "TestProject"
        project_dir.mkdir()
        settings_dir = project_dir / "ProjectSettings"
        settings_dir.mkdir()

        version_file = settings_dir / "ProjectVersion.txt"
        version_file.write_text("m_EditorVersion: invalid.version.string\n")

        version = parse_project_version(project_dir)
        assert version is None


class TestGetUnityInstallations:
    """Test detection of Unity installations."""

    @patch('platform.system')
    @patch('pathlib.Path.home')
    def test_get_installations_macos(self, mock_home, mock_system):
        """Test getting Unity installations on macOS."""
        mock_system.return_value = "Darwin"
        mock_home.return_value = Path("/Users/test")

        # Mock the editors directory structure
        with patch('pathlib.Path.exists') as mock_exists, \
             patch('pathlib.Path.iterdir') as mock_iterdir:

            mock_exists.return_value = True
            mock_iterdir.return_value = [
                Path("/Users/test/Library/Application Support/UnityHub/editors/2021.3.15f1"),
                Path("/Users/test/Library/Application Support/UnityHub/editors/2022.2.0f1"),
            ]

            installations = get_unity_installations()

            assert len(installations) == 2
            assert installations[0]['version'] == '2022.2.0f1'  # Should be sorted newest first
            assert installations[1]['version'] == '2021.3.15f1'

    @patch('platform.system')
    @patch('pathlib.Path.home')
    def test_get_installations_windows(self, mock_home, mock_system):
        """Test getting Unity installations on Windows."""
        mock_system.return_value = "Windows"
        mock_home.return_value = Path("C:/Users/test")

        with patch('pathlib.Path.exists') as mock_exists, \
             patch('pathlib.Path.iterdir') as mock_iterdir:

            mock_exists.return_value = True
            mock_iterdir.return_value = [
                Path("C:/Users/test/AppData/Roaming/UnityHub/editors/2021.3.15f1"),
            ]

            installations = get_unity_installations()

            assert len(installations) == 1
            assert installations[0]['version'] == '2021.3.15f1'

    @patch('platform.system')
    def test_get_installations_unsupported_platform(self, mock_system):
        """Test handling unsupported platforms."""
        mock_system.return_value = "Unsupported"

        installations = get_unity_installations()
        assert installations == []

    @patch('platform.system')
    @patch('pathlib.Path.home')
    def test_get_installations_missing_directory(self, mock_home, mock_system):
        """Test handling missing editors directory."""
        mock_system.return_value = "Darwin"
        mock_home.return_value = Path("/Users/test")

        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = False

            installations = get_unity_installations()
            assert installations == []


class TestGetUnityCachePaths:
    """Test Unity cache path resolution."""

    @patch('platform.system')
    @patch('pathlib.Path.home')
    def test_cache_paths_macos(self, mock_home, mock_system):
        """Test cache paths on macOS."""
        mock_system.return_value = "Darwin"
        mock_home.return_value = Path("/Users/test")

        paths = get_unity_cache_paths()

        assert 'global_cache' in paths
        assert 'package_cache' in paths
        assert 'asset_store' in paths
        assert paths['global_cache'] == '/Users/test/Library/Unity/cache'
        assert paths['package_cache'] == '/Users/test/Library/Unity/cache/packages'

    @patch('platform.system')
    @patch('pathlib.Path.home')
    def test_cache_paths_windows(self, mock_home, mock_system):
        """Test cache paths on Windows."""
        mock_system.return_value = "Windows"
        mock_home.return_value = Path("C:/Users/test")

        paths = get_unity_cache_paths()

        assert paths['global_cache'] == 'C:\\Users\\test\\AppData\\Local\\Unity\\cache'
        assert paths['package_cache'] == 'C:\\Users\\test\\AppData\\Local\\Unity\\cache\\packages'

    @patch('platform.system')
    @patch('pathlib.Path.home')
    def test_cache_paths_linux(self, mock_home, mock_system):
        """Test cache paths on Linux."""
        mock_system.return_value = "Linux"
        mock_home.return_value = Path("/home/test")

        paths = get_unity_cache_paths()

        assert paths['global_cache'] == '/home/test/.cache/unity3d'
        assert paths['package_cache'] == '/home/test/.cache/unity3d/Packages'

    @patch('platform.system')
    @patch('pathlib.Path.home')
    def test_cache_paths_with_version(self, mock_home, mock_system):
        """Test cache paths with version-specific subdirectories."""
        mock_system.return_value = "Darwin"
        mock_home.return_value = Path("/Users/test")

        version = UnityVersion(major=2021, minor=3, patch=15, full_version="2021.3.15f1")

        with patch('pathlib.Path.exists') as mock_exists:
            # Mock that versioned directory exists
            def mock_exists_func(path):
                return "2021.3" in str(path)

            mock_exists.side_effect = mock_exists_func

            paths = get_unity_cache_paths(version)

            # Should return versioned paths where they exist
            assert "2021.3" in paths['global_cache']


class TestFindMatchingUnityInstallation:
    """Test finding matching Unity installations."""

    def test_find_exact_match(self):
        """Test finding exact version match."""
        project_version = UnityVersion(major=2021, minor=3, patch=15, full_version="2021.3.15f1")

        with patch('helpers.unity_version.get_unity_installations') as mock_get_installs:
            mock_get_installs.return_value = [
                {'version': '2021.3.15f1', 'path': '/path/to/unity'},
                {'version': '2022.2.0f1', 'path': '/path/to/unity2'},
            ]

            result = find_matching_unity_installation(project_version)
            assert result is not None
            assert result['version'] == '2021.3.15f1'

    def test_find_compatible_match(self):
        """Test finding compatible version when exact match doesn't exist."""
        project_version = UnityVersion(major=2021, minor=3, patch=15, full_version="2021.3.15f1")

        with patch('helpers.unity_version.get_unity_installations') as mock_get_installs:
            mock_get_installs.return_value = [
                {'version': '2021.3.16f1', 'path': '/path/to/unity'},  # Compatible (same major.minor)
                {'version': '2022.2.0f1', 'path': '/path/to/unity2'},  # Different major.minor
            ]

            result = find_matching_unity_installation(project_version)
            assert result is not None
            assert result['version'] == '2021.3.16f1'

    def test_no_match_found(self):
        """Test when no compatible installation is found."""
        project_version = UnityVersion(major=2021, minor=3, patch=15, full_version="2021.3.15f1")

        with patch('helpers.unity_version.get_unity_installations') as mock_get_installs:
            mock_get_installs.return_value = [
                {'version': '2022.2.0f1', 'path': '/path/to/unity'},  # Different major.minor
            ]

            result = find_matching_unity_installation(project_version)
            assert result is None