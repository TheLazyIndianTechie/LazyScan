"""Integration tests for Unreal Engine version detection and cache management."""

import pytest
import json
import os
from pathlib import Path
from unittest.mock import patch, mock_open
from helpers.unreal_version import (
    parse_uproject_metadata,
    resolve_engine_version,
    parse_epic_manifests,
    resolve_engine_install_path,
    discover_unreal_project,
)
from helpers.unreal_cache_helpers import generate_unreal_project_report


class TestUprojectParsing:
    """Test .uproject file parsing functionality."""

    def test_parse_valid_uproject(self, tmp_path):
        """Test parsing a valid .uproject file."""
        uproject_file = tmp_path / "TestProject.uproject"
        project_data = {
            "FileVersion": 3,
            "EngineAssociation": "5.3",
            "Category": "",
            "Description": "",
            "Modules": [],
            "Plugins": []
        }

        uproject_file.write_text(json.dumps(project_data, indent=2))

        metadata = parse_uproject_metadata(uproject_file)
        assert metadata is not None
        assert metadata["EngineAssociation"] == "5.3"

    def test_parse_uproject_with_json_engine_association(self, tmp_path):
        """Test parsing .uproject with JSON-formatted EngineAssociation."""
        uproject_file = tmp_path / "TestProject.uproject"
        project_data = {
            "EngineAssociation": '{"Version": "5.2", "Identifier": "UE_5.2"}',
            "FileVersion": 3
        }

        uproject_file.write_text(json.dumps(project_data, indent=2))

        metadata = parse_uproject_metadata(uproject_file)
        assert metadata is not None
        assert metadata["EngineAssociation"] == '{"Version": "5.2", "Identifier": "UE_5.2"}'

    def test_parse_invalid_uproject(self, tmp_path):
        """Test parsing an invalid .uproject file."""
        uproject_file = tmp_path / "InvalidProject.uproject"
        uproject_file.write_text("invalid json content")

        metadata = parse_uproject_metadata(uproject_file)
        assert metadata is None

    def test_parse_nonexistent_uproject(self):
        """Test parsing a non-existent .uproject file."""
        with pytest.raises(FileNotFoundError):
            parse_uproject_metadata(Path("/nonexistent/file.uproject"))


class TestEngineVersionResolution:
    """Test engine version resolution from various formats."""

    def test_resolve_direct_version(self):
        """Test resolving direct version strings."""
        assert resolve_engine_version("5.3") == "5.3"
        assert resolve_engine_version("4.27") == "4.27"
        assert resolve_engine_version("5.3.2") == "5.3.2"

    def test_resolve_json_engine_association(self):
        """Test resolving JSON-formatted EngineAssociation."""
        json_assoc = '{"Version": "5.2", "Identifier": "UE_5.2"}'
        assert resolve_engine_version(json_assoc) == "5.2"

        json_assoc = '{"Identifier": "UE_5.1"}'
        assert resolve_engine_version(json_assoc) == "UE_5.1"

    def test_resolve_common_identifiers(self):
        """Test resolving common UE identifier formats."""
        assert resolve_engine_version("UE_5.3") == "5.3"
        assert resolve_engine_version("UE_5.2") == "5.2"
        assert resolve_engine_version("UE_4.27") == "4.27"

    def test_resolve_none_input(self):
        """Test resolving None input."""
        assert resolve_engine_version(None) is None
        assert resolve_engine_version("") is None


class TestEpicManifestParsing:
    """Test Epic Games Launcher manifest parsing."""

    @patch('helpers.unreal_version.find_epic_manifests')
    def test_parse_epic_manifests_with_mock_data(self, mock_find_manifests, tmp_path):
        """Test parsing mocked Epic manifests."""
        # Create mock manifest directory
        manifest_dir = tmp_path / "MockManifest"
        manifest_dir.mkdir()

        # Create mock manifest files
        manifest1 = manifest_dir / "UE_5.3.item"
        manifest_data1 = {
            "AppName": "UE_5.3",
            "CatalogNamespace": "ue",
            "DisplayName": "Unreal Engine 5.3",
            "AppVersionString": "5.3.0",
            "InstallLocation": str(tmp_path / "UE_5.3_install")
        }
        manifest1.write_text(json.dumps(manifest_data1))

        manifest2 = manifest_dir / "SomeOtherApp.item"
        manifest_data2 = {
            "AppName": "SomeOtherApp",
            "CatalogNamespace": "other",
            "InstallLocation": str(tmp_path / "other_install")
        }
        manifest2.write_text(json.dumps(manifest_data2))

        mock_find_manifests.return_value = [manifest_dir]

        engines = parse_epic_manifests()

        assert "UE_5.3" in engines
        assert engines["UE_5.3"]["version"] == "5.3.0"
        assert engines["UE_5.3"]["install_location"] == tmp_path / "UE_5.3_install"
        assert "SomeOtherApp" not in engines  # Should filter out non-ue namespace

    @patch('helpers.unreal_version.find_epic_manifests')
    def test_resolve_engine_install_path(self, mock_find_manifests, tmp_path):
        """Test resolving engine install paths from manifests."""
        manifest_dir = tmp_path / "MockManifest"
        manifest_dir.mkdir()

        # Create mock manifest
        manifest = manifest_dir / "UE_5.3.item"
        manifest_data = {
            "AppName": "UE_5.3",
            "CatalogNamespace": "ue",
            "AppVersionString": "5.3.0",
            "InstallLocation": str(tmp_path / "UE_5.3_install")
        }
        manifest.write_text(json.dumps(manifest_data))

        mock_find_manifests.return_value = [manifest_dir]

        engines = parse_epic_manifests()
        install_path = resolve_engine_install_path("5.3", engines)

        assert install_path == tmp_path / "UE_5.3_install"

    @patch('helpers.unreal_version.find_epic_manifests')
    def test_resolve_engine_install_path_partial_match(self, mock_find_manifests, tmp_path):
        """Test resolving engine paths with partial version matches."""
        manifest_dir = tmp_path / "MockManifest"
        manifest_dir.mkdir()

        manifest = manifest_dir / "UE_5.3.item"
        manifest_data = {
            "AppName": "UE_5.3",
            "CatalogNamespace": "ue",
            "AppVersionString": "5.3.2",
            "InstallLocation": str(tmp_path / "UE_5.3_install")
        }
        manifest.write_text(json.dumps(manifest_data))

        mock_find_manifests.return_value = [manifest_dir]

        engines = parse_epic_manifests()
        install_path = resolve_engine_install_path("5.3", engines)  # Should match 5.3.2

        assert install_path == tmp_path / "UE_5.3_install"


class TestUnrealProjectDiscovery:
    """Test full Unreal project discovery functionality."""

    def test_discover_unreal_project_basic(self, tmp_path):
        """Test basic Unreal project discovery."""
        project_dir = tmp_path / "TestUnrealProject"
        project_dir.mkdir()

        uproject_file = project_dir / "TestUnrealProject.uproject"
        project_data = {
            "FileVersion": 3,
            "EngineAssociation": "5.3",
            "Category": "",
            "Description": "",
            "Modules": [],
            "Plugins": []
        }
        uproject_file.write_text(json.dumps(project_data, indent=2))

        # Create some cache directories
        (project_dir / "DerivedDataCache").mkdir()
        (project_dir / "Intermediate").mkdir()

        with patch('helpers.unreal_version.parse_epic_manifests') as mock_parse:
            with patch('helpers.unreal_version.resolve_engine_install_path') as mock_resolve:
                mock_parse.return_value = {}
                mock_resolve.return_value = None

                project = discover_unreal_project(uproject_file)

                assert project.name == "TestUnrealProject"
                assert project.engine_version == "5.3"
                assert len(project.caches) >= 2  # At least DerivedDataCache and Intermediate

                # Check that caches include expected directories
                cache_names = [cache.name for cache in project.caches]
                assert "DerivedDataCache" in cache_names
                assert "Intermediate" in cache_names

    def test_discover_unreal_project_with_engine_caches(self, tmp_path):
        """Test project discovery with engine-level caches."""
        project_dir = tmp_path / "TestUnrealProject"
        project_dir.mkdir()

        uproject_file = project_dir / "TestUnrealProject.uproject"
        project_data = {"EngineAssociation": "5.3"}
        uproject_file.write_text(json.dumps(project_data))

        # Mock engine installation
        engine_dir = tmp_path / "UE_5.3"
        engine_dir.mkdir()
        (engine_dir / "Engine" / "DerivedDataCache").mkdir(parents=True)

        with patch('helpers.unreal_version.parse_epic_manifests') as mock_parse:
            with patch('helpers.unreal_version.resolve_engine_install_path') as mock_resolve:
                mock_parse.return_value = {"UE_5.3": {"install_location": engine_dir}}
                mock_resolve.return_value = engine_dir

                project = discover_unreal_project(uproject_file)

                # Should include engine-level cache
                cache_names = [cache.name for cache in project.caches]
                assert "Engine/DerivedDataCache" in cache_names


class TestCacheReportGeneration:
    """Test enhanced cache report generation with metadata."""

    def test_generate_report_with_engine_version(self, tmp_path):
        """Test report generation includes engine version."""
        project_dir = tmp_path / "TestProject"
        project_dir.mkdir()

        uproject_file = project_dir / "TestProject.uproject"
        project_data = {"EngineAssociation": "5.3"}
        uproject_file.write_text(json.dumps(project_data))

        # Create cache directory
        cache_dir = project_dir / "DerivedDataCache"
        cache_dir.mkdir()
        (cache_dir / "test.dat").write_bytes(b"x" * 1000)

        report = generate_unreal_project_report(str(project_dir))

        assert report["engine_version"] == "5.3"
        assert "DerivedDataCache" in report["cache_dirs"]
        assert report["cache_dirs"]["DerivedDataCache"]["warn_on_delete"] is True
        assert "rebuild required" in report["cache_dirs"]["DerivedDataCache"]["description"]

    def test_generate_report_cache_metadata(self, tmp_path):
        """Test cache metadata includes proper flags and descriptions."""
        project_dir = tmp_path / "TestProject"
        project_dir.mkdir()

        uproject_file = project_dir / "TestProject.uproject"
        project_data = {"EngineAssociation": "5.3"}
        uproject_file.write_text(json.dumps(project_data))

        # Create various cache directories
        (project_dir / "DerivedDataCache").mkdir()
        (project_dir / "Intermediate").mkdir()
        (project_dir / "Saved" / "Logs").mkdir(parents=True)
        (project_dir / "Binaries").mkdir()

        report = generate_unreal_project_report(str(project_dir))

        # Check rebuild-required caches
        assert report["cache_dirs"]["DerivedDataCache"]["warn_on_delete"] is True
        assert report["cache_dirs"]["Intermediate"]["warn_on_delete"] is True
        assert report["cache_dirs"]["Binaries"]["warn_on_delete"] is True

        # Check safe caches
        assert report["cache_dirs"]["Saved/Logs"]["warn_on_delete"] is False

    def test_generate_report_marketplace_caches(self, tmp_path):
        """Test marketplace cache detection."""
        project_dir = tmp_path / "TestProject"
        project_dir.mkdir()

        uproject_file = project_dir / "TestProject.uproject"
        project_data = {"EngineAssociation": "5.3"}
        uproject_file.write_text(json.dumps(project_data))

        report = generate_unreal_project_report(str(project_dir))

        # Should include marketplace cache (may not exist but should be listed)
        assert "MarketplaceAssets" in report["cache_dirs"]


class TestSecurityIntegration:
    """Test SecuritySentinel integration with Unreal operations."""

    @patch('lazyscan.security.sentinel.get_sentinel')
    def test_secure_delete_with_unreal_context(self, mock_get_sentinel, tmp_path):
        """Test that secure_delete uses Unreal context for SecuritySentinel."""
        from helpers.secure_operations import SecureOperationManager
        secure_ops = SecureOperationManager()

        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        # Mock sentinel
        mock_sentinel = mock_get_sentinel.return_value

        # Call secure_delete with unreal context
        result = secure_ops.secure_delete_paths([str(test_file)], "Test Operation", "unreal")

        # Verify sentinel was called with unreal context
        mock_sentinel.guard_delete.assert_called()
        call_args = mock_sentinel.guard_delete.call_args
        assert call_args[0][1] == "unreal"  # context parameter

        assert result.success is True


if __name__ == "__main__":
    pytest.main([__file__])