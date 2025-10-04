#!/usr/bin/env python3
"""
Tests for the cache command functionality.
"""

import pytest
from unittest.mock import patch, MagicMock
from lazyscan.cli.main_argparse import handle_cache_command


class TestCacheCommand:
    """Test the cache command handler."""

    @patch('lazyscan.cli.main_argparse.get_config')
    @patch('lazyscan.cli.main_argparse.get_typed_config')
    @patch('lazyscan.cli.main_argparse.console')
    def test_cache_command_macos_dry_run(self, mock_console, mock_get_typed_config, mock_get_config):
        """Test cache command with macOS platform in dry-run mode."""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.get.return_value = {}
        mock_get_config.return_value = mock_config

        mock_security_config = MagicMock()
        mock_security_config.__dict__ = {
            "allow_admin_operations": False,
            "confirm_deletions": True,
            "safe_delete_enabled": True
        }
        # Create a simple object with security attribute
        class MockTypedConfig:
            def __init__(self, security):
                self.security = security

        mock_typed_config = MockTypedConfig(mock_security_config)
        mock_get_typed_config.return_value = mock_typed_config

        # Mock platform import
        with patch('lazyscan.cli.main_argparse.sys') as mock_sys:
            mock_sys.platform = "darwin"

            with patch('lazyscan.platforms.macos.get_macos_cache_targets') as mock_get_targets:
                # Mock cache targets
                mock_targets = [
                    MagicMock(category="package_manager", safety_level=MagicMock(name="SAFE"), path="/tmp/homebrew", retention_days=30),
                    MagicMock(category="package_manager", safety_level=MagicMock(name="SAFE"), path="/tmp/npm", retention_days=90),
                ]
                mock_get_targets.return_value = mock_targets

                # Mock retention policy engine
                with patch('lazyscan.core.retention_policy.RetentionPolicyEngine') as mock_engine_class:
                    mock_engine = MagicMock()
                    mock_engine.apply_retention_policies.return_value = []
                    mock_engine.get_cleanup_summary.return_value = {
                        "total_operations": 2,
                        "successful_operations": 2,
                        "skipped_operations": 0,
                        "failed_operations": 0,
                        "total_files_deleted": 0,
                        "total_size_mb": 0.0,
                        "operations": []
                    }
                    mock_engine_class.return_value = mock_engine

                    # Create mock args
                    args = MagicMock()
                    args.platform = "auto"
                    args.dry_run = True
                    args.force = True  # Skip confirmation
                    args.include_docker = False
                    args.targets = None

                    # Call the handler
                    handle_cache_command(args)

                    # Verify calls
                    mock_get_targets.assert_called_once_with({})
                    mock_engine.apply_retention_policies.assert_called_once_with(mock_targets, dry_run=True, force=True)
                    mock_console.print.assert_called()  # Should have printed output

    @patch('lazyscan.cli.main_argparse.get_config')
    @patch('lazyscan.cli.main_argparse.console')
    def test_cache_command_unknown_platform(self, mock_console, mock_get_config):
        """Test cache command with unknown platform."""
        mock_config = MagicMock()
        mock_config.get.return_value = {}
        mock_get_config.return_value = mock_config

        with patch('lazyscan.cli.main_argparse.sys') as mock_sys:
            mock_sys.platform = "unknown"

            args = MagicMock()
            args.platform = "auto"
            args.dry_run = True
            args.force = False
            args.include_docker = False
            args.targets = None

            handle_cache_command(args)

            # Should print error message
            mock_console.print.assert_called()
            error_calls = [call for call in mock_console.print.call_args_list if "Unsupported platform" in str(call)]
            assert len(error_calls) > 0

    @patch('lazyscan.cli.main_argparse.get_config')
    @patch('lazyscan.cli.main_argparse.get_typed_config')
    @patch('lazyscan.cli.main_argparse.console')
    def test_cache_command_with_docker(self, mock_console, mock_get_typed_config, mock_get_config):
        """Test cache command with Docker integration."""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.get.return_value = {}
        mock_get_config.return_value = mock_config

        mock_security_config = MagicMock()
        mock_security_config.__dict__ = {
            "allow_admin_operations": False,
            "confirm_deletions": True,
            "safe_delete_enabled": True
        }
        # Create a simple object with security attribute
        class MockTypedConfig:
            def __init__(self, security):
                self.security = security

        mock_typed_config = MockTypedConfig(mock_security_config)
        mock_get_typed_config.return_value = mock_typed_config

        with patch('lazyscan.cli.main_argparse.sys') as mock_sys:
            mock_sys.platform = "darwin"

            with patch('lazyscan.platforms.macos.get_macos_cache_targets') as mock_get_targets:
                mock_get_targets.return_value = [MagicMock()]  # Return one target to avoid early exit

                with patch('lazyscan.core.docker_integration.DockerIntegration') as mock_docker_class:
                    mock_docker = MagicMock()
                    mock_docker.is_available.return_value = True
                    mock_docker.estimate_cleanup_size.return_value = {"estimated_mb": 100.0}
                    mock_docker.perform_cleanup.return_value = {"success": True}
                    mock_docker_class.return_value = mock_docker

                    with patch('builtins.input', return_value='y'):  # Mock user confirmation
                        args = MagicMock()
                        args.platform = "auto"
                        args.dry_run = False
                        args.force = False
                        args.include_docker = True
                        args.targets = None

                        handle_cache_command(args)

                        # Verify Docker integration was called
                        mock_docker.is_available.assert_called()
                        mock_docker.estimate_cleanup_size.assert_called()
                        mock_docker.perform_cleanup.assert_called_once_with(volumes=False, dry_run=False, force=True)