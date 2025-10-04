#!/usr/bin/env python3
"""
Tests for Docker integration functionality.
"""

import pytest
from unittest.mock import patch, MagicMock
from lazyscan.core.docker_integration import DockerIntegration


class TestDockerIntegration:
    """Test Docker integration functionality."""

    def test_docker_not_available_by_default(self):
        """Test that Docker is not available by default on test systems."""
        docker = DockerIntegration()
        assert not docker.is_available()

    @patch('subprocess.run')
    def test_docker_available_when_command_succeeds(self, mock_run):
        """Test that Docker is detected as available when version command succeeds."""
        # Mock successful docker --version
        mock_run.return_value = MagicMock(returncode=0, stdout="Docker version 24.0.0")

        docker = DockerIntegration()
        assert docker.is_available()

    @patch('subprocess.run')
    def test_docker_not_available_when_command_fails(self, mock_run):
        """Test that Docker is not available when version command fails."""
        # Mock failed docker --version
        mock_run.side_effect = FileNotFoundError("docker command not found")

        docker = DockerIntegration()
        assert not docker.is_available()

    @patch('subprocess.run')
    def test_get_system_df_info_dry_run(self, mock_run):
        """Test getting Docker system df info in dry-run mode."""
        # Mock successful docker system df
        mock_output = """TYPE            TOTAL     ACTIVE    SIZE      RECLAIMABLE
Images          24        12        8.9GB     4.5GB
Containers      5         2         2.1GB     1.2GB
Local Volumes   15        8         3.2GB     2.8GB
Build Cache     0         0         0B        0B
"""
        mock_run.return_value = MagicMock(returncode=0, stdout=mock_output)

        docker = DockerIntegration()
        # Force docker to be available for this test
        docker.docker_available = True

        result = docker.get_system_df_info(dry_run=True)

        assert "dry_run" in result
        assert result["dry_run"] is True
        assert "items" in result
        assert len(result["items"]) == 4

        # Check first item
        images = result["items"][0]
        assert images["type"] == "Images"
        assert images["total_count"] == "24"
        assert images["reclaimable"] == "4.5GB"

    @patch('subprocess.run')
    def test_get_system_df_info_command_failure(self, mock_run):
        """Test handling of docker system df command failure."""
        mock_run.return_value = MagicMock(returncode=1, stderr="docker daemon not running")

        docker = DockerIntegration()
        docker.docker_available = True

        result = docker.get_system_df_info(dry_run=True)

        assert "error" in result
        assert "docker daemon not running" in result["error"]

    def test_get_system_df_info_docker_not_available(self):
        """Test that system df info returns error when Docker not available."""
        docker = DockerIntegration()
        # Docker not available by default

        result = docker.get_system_df_info()

        assert "error" in result
        assert "Docker not available" in result["error"]

    @patch('subprocess.run')
    def test_estimate_cleanup_size(self, mock_run):
        """Test estimating cleanup size from Docker system df."""
        mock_output = """TYPE            TOTAL     ACTIVE    SIZE      RECLAIMABLE
Images          24        12        8.9GB     4.5GB
Containers      5         2         2.1GB     1.2GB
Local Volumes   15        8         3.2GB     2.8GB
"""
        mock_run.return_value = MagicMock(returncode=0, stdout=mock_output)

        docker = DockerIntegration()
        docker.docker_available = True

        result = docker.estimate_cleanup_size()

        assert "estimated_mb" in result
        # 4.5GB + 1.2GB + 2.8GB = 8.5GB = 8704 MB (approximately)
        assert result["estimated_mb"] > 8000  # Should be around 8704 MB
        assert "breakdown" in result

    def test_estimate_cleanup_size_docker_not_available(self):
        """Test cleanup size estimation when Docker not available."""
        docker = DockerIntegration()

        result = docker.estimate_cleanup_size()

        assert "error" in result
        assert "Docker not available" in result["error"]
        assert result["estimated_mb"] == 0

    @patch('subprocess.run')
    def test_perform_cleanup_dry_run(self, mock_run):
        """Test performing Docker cleanup in dry-run mode."""
        mock_run.return_value = MagicMock(returncode=0, stdout="Would remove: ...")

        docker = DockerIntegration()
        docker.docker_available = True

        result = docker.perform_cleanup(dry_run=True)

        assert result["success"] is True
        assert result["dry_run"] is True
        assert "docker system prune --all --dry-run" in result["command"]
        assert "output" in result

    @patch('lazyscan.core.docker_integration.DockerIntegration._check_docker_availability')
    def test_perform_cleanup_with_volumes_requires_force(self, mock_check):
        """Test that volume cleanup requires force flag."""
        mock_check.return_value = True

        docker = DockerIntegration()
        # docker_available is set to True by mocked _check_docker_availability

        result = docker.perform_cleanup(volumes=True, force=False)

        assert result["success"] is False
        assert "requires_confirmation" in result
        assert result["requires_confirmation"] is True

    @patch('subprocess.run')
    def test_perform_cleanup_with_volumes_and_force(self, mock_run):
        """Test performing Docker cleanup with volumes when forced."""
        mock_run.return_value = MagicMock(returncode=0, stdout="Total reclaimed space: 2.5GB")

        docker = DockerIntegration()
        docker.docker_available = True

        result = docker.perform_cleanup(volumes=True, force=True, dry_run=False)

        assert result["success"] is True
        assert result["dry_run"] is False
        assert "--volumes" in result["command"]
        assert result["space_reclaimed"] > 2500  # Should be around 2560 MB for 2.5GB

    def test_perform_cleanup_docker_not_available(self):
        """Test cleanup when Docker is not available."""
        docker = DockerIntegration()

        result = docker.perform_cleanup()

        assert result["success"] is False
        assert "error" in result
        assert "Docker not available" in result["error"]

    @patch('subprocess.run')
    def test_get_docker_info_success(self, mock_run):
        """Test getting Docker info when available."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="Docker version 24.0.0, build abc123"),  # __init__ check
            MagicMock(returncode=0, stdout="Docker version 24.0.0, build abc123"),  # version check
            MagicMock(returncode=0, stdout="Docker system info here...")  # system info
        ]

        docker = DockerIntegration()
        # docker_available is already set to True by the mocked __init__

        result = docker.get_docker_info()

        assert result["available"] is True
        assert "Docker version 24.0.0" in result["version"]
        assert "system_info" in result

    def test_get_docker_info_not_available(self):
        """Test getting Docker info when not available."""
        docker = DockerIntegration()

        result = docker.get_docker_info()

        assert result["available"] is False
        assert "error" in result

    def test_parse_size_to_mb(self):
        """Test parsing various size formats to MB."""
        docker = DockerIntegration()

        # Test different units
        assert docker._parse_size_to_mb("1024B") == 1024 / (1024 * 1024)  # ~0.001 MB
        assert docker._parse_size_to_mb("1KB") == 1 / 1024  # ~0.001 MB
        assert docker._parse_size_to_mb("1MB") == 1.0
        assert docker._parse_size_to_mb("1GB") == 1024.0
        assert docker._parse_size_to_mb("1TB") == 1024 * 1024

        # Test edge cases
        assert docker._parse_size_to_mb("0B") == 0.0
        assert docker._parse_size_to_mb("") == 0.0
        assert docker._parse_size_to_mb("invalid") == 0.0