#!/usr/bin/env python3
"""
Tests for audit log migration functionality.
"""

import json
import os
import tempfile
import shutil
import pathlib
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from lazyscan.security.audit_encryption_schema import AuditEncryptionConfig, AuditCompatibilityConfig
from lazyscan.security.audit_migration import (
    AuditMigrationManager,
    AuditDirectoryInfo,
    MigrationCheckpoint,
    MigrationStatus,
    MigrationPhase,
    detect_migration_needed,
    get_audit_migration_manager
)


class TestAuditDirectoryInfo:
    """Test AuditDirectoryInfo dataclass."""

    def test_plaintext_detection(self):
        """Test plaintext file detection."""
        info = AuditDirectoryInfo(
            platform="test",
            path=Path("/tmp/test"),
            exists=True,
            total_files=2,
            plaintext_files=["file1.log", "file2.jsonl"],
            encrypted_files=[],
            mixed_state=False
        )

        assert info.has_plaintext_logs() is True
        assert info.is_fully_encrypted() is False
        assert info.needs_migration() is True

    def test_encrypted_detection(self):
        """Test encrypted file detection."""
        info = AuditDirectoryInfo(
            platform="test",
            path=Path("/tmp/test"),
            exists=True,
            total_files=1,
            plaintext_files=[],
            encrypted_files=["file1.enc"],
            mixed_state=False
        )

        assert info.has_plaintext_logs() is False
        assert info.is_fully_encrypted() is True
        assert info.needs_migration() is False

    def test_mixed_state_detection(self):
        """Test mixed state detection."""
        info = AuditDirectoryInfo(
            platform="test",
            path=Path("/tmp/test"),
            exists=True,
            total_files=2,
            plaintext_files=["file1.log"],
            encrypted_files=["file2.enc"],
            mixed_state=True
        )

        assert info.has_plaintext_logs() is True
        assert info.is_fully_encrypted() is False
        assert info.needs_migration() is True
        assert info.mixed_state is True


class TestMigrationCheckpoint:
    """Test MigrationCheckpoint dataclass."""

    def test_checkpoint_creation(self):
        """Test checkpoint creation and serialization."""
        checkpoint = MigrationCheckpoint(
            migration_id="test-123",
            phase="encryption",
            status="in_progress",
            processed_files=["file1.log"],
            failed_files=[],
            total_files=5,
            start_time="2024-01-01T00:00:00Z",
            last_update="2024-01-01T00:01:00Z",
            metadata={"test": "data"}
        )

        # Test serialization
        data = checkpoint.to_dict()
        assert data["migration_id"] == "test-123"
        assert data["phase"] == "encryption"
        assert data["processed_files"] == ["file1.log"]

        # Test deserialization
        restored = MigrationCheckpoint.from_dict(data)
        assert restored.migration_id == checkpoint.migration_id
        assert restored.phase == checkpoint.phase

    def test_progress_update(self):
        """Test progress update functionality."""
        checkpoint = MigrationCheckpoint(
            migration_id="test-123",
            phase="encryption",
            status="in_progress",
            processed_files=[],
            failed_files=[],
            total_files=2,
            start_time="2024-01-01T00:00:00Z",
            last_update="2024-01-01T00:00:00Z",
            metadata={}
        )

        # Update with success
        checkpoint.update_progress("file1.log", success=True)
        assert "file1.log" in checkpoint.processed_files
        assert len(checkpoint.failed_files) == 0

        # Update with failure
        checkpoint.update_progress("file2.log", success=False)
        assert "file2.log" in checkpoint.failed_files
        assert len(checkpoint.processed_files) == 1


class TestAuditMigrationManager:
    """Test AuditMigrationManager functionality."""

    @pytest.fixture
    def encryption_config(self):
        """Create test encryption config."""
        return AuditEncryptionConfig()

    @pytest.fixture
    def compatibility_config(self):
        """Create test compatibility config."""
        return AuditCompatibilityConfig()

    @pytest.fixture
    def manager(self, encryption_config, compatibility_config):
        """Create test migration manager."""
        return AuditMigrationManager(encryption_config, compatibility_config)

    def test_initialization(self, manager):
        """Test manager initialization."""
        assert manager.encryption_config is not None
        assert manager.compatibility_config is not None
        assert manager.migration_id is not None
        assert len(manager.migration_id) == 16  # Should be 16 char hash

    def test_platform_directories(self, manager):
        """Test platform-specific directory detection."""
        dirs = manager.audit_dirs

        # Should have directories for current platform
        assert len(dirs) > 0

        # Check that paths are strings
        for path in dirs.values():
            assert isinstance(path, str)

    @patch('sys.platform', 'darwin')
    def test_macos_directory_detection(self, encryption_config, compatibility_config):
        """Test macOS directory detection."""
        manager = AuditMigrationManager(encryption_config, compatibility_config)
        dirs = manager.audit_dirs

        assert "macos" in dirs
        expected_path = Path.home() / "Library" / "Logs" / "LazyScan"
        assert dirs["macos"] == str(expected_path)

    @patch('lazyscan.security.audit_migration.AuditMigrationManager._get_platform_audit_dirs', return_value={"windows": "/tmp/test_appdata/LazyScan/Logs"})
    def test_windows_directory_detection(self, mock_get_dirs, encryption_config, compatibility_config):
        """Test Windows directory detection."""
        manager = AuditMigrationManager(encryption_config, compatibility_config)
        dirs = manager.audit_dirs

        assert "windows" in dirs
        expected_path = "/tmp/test_appdata/LazyScan/Logs"
        assert dirs["windows"] == expected_path

    def test_linux_directory_detection(self, encryption_config, compatibility_config):
        """Test Linux directory detection."""
        with patch('sys.platform', 'linux'):
            manager = AuditMigrationManager(encryption_config, compatibility_config)
            dirs = manager.audit_dirs

            assert "linux" in dirs
            expected_path = Path.home() / ".local" / "share" / "lazyscan" / "logs"
            assert dirs["linux"] == str(expected_path)

    def test_directory_analysis_nonexistent(self, manager, tmp_path):
        """Test directory analysis for nonexistent directory."""
        info = manager._analyze_directory("test", tmp_path / "nonexistent")

        assert info.platform == "test"
        assert info.exists is False
        assert info.total_files == 0
        assert len(info.plaintext_files) == 0
        assert len(info.encrypted_files) == 0

    def test_directory_analysis_with_files(self, manager, tmp_path):
        """Test directory analysis with actual files."""
        # Create test directory with files
        test_dir = tmp_path / "test_logs"
        test_dir.mkdir()

        # Create plaintext files
        (test_dir / "audit.log").write_text("test log entry")
        (test_dir / "audit.jsonl").write_text('{"test": "entry"}')

        # Create empty file (should be ignored)
        (test_dir / "empty.log").write_text("")

        # Create encrypted file
        (test_dir / "encrypted.enc").write_text("encrypted data")

        info = manager._analyze_directory("test", test_dir)

        assert info.platform == "test"
        assert info.exists is True
        assert info.total_files == 3  # 2 plaintext + 1 encrypted
        assert len(info.plaintext_files) == 2
        assert len(info.encrypted_files) == 1
        assert str(test_dir / "audit.log") in info.plaintext_files
        assert str(test_dir / "audit.jsonl") in info.plaintext_files
        assert str(test_dir / "encrypted.enc") in info.encrypted_files

    def test_migration_planning(self, manager):
        """Test migration plan creation."""
        directories = [
            AuditDirectoryInfo(
                platform="test1",
                path=Path("/tmp/test1"),
                exists=True,
                total_files=2,
                plaintext_files=["file1.log", "file2.jsonl"],
                encrypted_files=[],
                mixed_state=False
            ),
            AuditDirectoryInfo(
                platform="test2",
                path=Path("/tmp/test2"),
                exists=True,
                total_files=1,
                plaintext_files=[],
                encrypted_files=["file1.enc"],
                mixed_state=False
            )
        ]

        plan = manager.plan_migration(directories)

        assert plan["requires_migration"] is True
        assert plan["total_plaintext_files"] == 2
        assert plan["total_encrypted_files"] == 1
        assert len(plan["directories"]) == 1  # Only test1 needs migration
        assert plan["directories"][0]["platform"] == "test1"

    def test_migration_planning_no_migration_needed(self, manager):
        """Test migration planning when no migration is needed."""
        directories = [
            AuditDirectoryInfo(
                platform="test",
                path=Path("/tmp/test"),
                exists=True,
                total_files=1,
                plaintext_files=[],
                encrypted_files=["file1.enc"],
                mixed_state=False
            )
        ]

        plan = manager.plan_migration(directories)

        assert plan["requires_migration"] is False
        assert plan["total_plaintext_files"] == 0
        assert len(plan["directories"]) == 0

    def test_checkpoint_save_load(self, manager, tmp_path):
        """Test checkpoint save and load functionality."""
        # Create a temporary checkpoint directory
        with patch.object(manager, '_get_checkpoint_dir', return_value=tmp_path / "checkpoints"):
            checkpoint = MigrationCheckpoint(
                migration_id="test-123",
                phase="test_phase",
                status="test_status",
                processed_files=["file1.log"],
                failed_files=[],
                total_files=1,
                start_time="2024-01-01T00:00:00Z",
                last_update="2024-01-01T00:01:00Z",
                metadata={"test": "data"}
            )

            # Save checkpoint
            manager._save_checkpoint(checkpoint)

            # Load checkpoint
            loaded = manager.load_checkpoint("test-123")

            assert loaded is not None
            assert loaded.migration_id == "test-123"
            assert loaded.phase == "test_phase"
            assert loaded.processed_files == ["file1.log"]


class TestMigrationDetection:
    """Test migration detection functionality."""

    @patch('lazyscan.security.audit_migration.AuditMigrationManager')
    def test_detect_migration_needed(self, mock_manager_class):
        """Test the detect_migration_needed function."""
        # Mock the manager and its methods
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_info = AuditDirectoryInfo(
            platform="test",
            path=Path("/tmp/test"),
            exists=True,
            total_files=1,
            plaintext_files=["test.log"],
            encrypted_files=[],
            mixed_state=False
        )
        mock_manager.detect_plaintext_directories.return_value = [mock_info]

        needed, results = detect_migration_needed()

        assert needed is True
        assert results["migration_needed"] is True
        assert len(results["directories"]) == 1

    def test_get_audit_migration_manager(self):
        """Test the get_audit_migration_manager factory function."""
        encryption_config = AuditEncryptionConfig()
        compatibility_config = AuditCompatibilityConfig()

        manager = get_audit_migration_manager(encryption_config, compatibility_config)

        assert isinstance(manager, AuditMigrationManager)
        assert manager.encryption_config == encryption_config
        assert manager.compatibility_config == compatibility_config


if __name__ == "__main__":
    pytest.main([__file__])