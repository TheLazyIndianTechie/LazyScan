#!/usr/bin/env python3
"""
Tests for LogReencryptionTool

This module contains comprehensive tests for the LogReencryptionTool class,
covering streaming re-encryption, checkpoint management, integrity verification,
and atomic operations.
"""

import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from lazyscan.security.log_reencryption_tool import (
    LogReencryptionTool,
    ReencryptionResult,
    ReencryptionStatus,
    ReencryptionPhase,
    ReencryptionBatch,
    ReencryptionCheckpoint,
    ReencryptionError,
    reencrypt_audit_log,
    get_reencryption_checkpoints,
)
from lazyscan.security.audit_encryption import AuditEncryption, EncryptedAuditEntry
from lazyscan.security.key_providers import KeyProvider


class MockKeyProvider(KeyProvider):
    """Mock key provider for testing."""

    def __init__(self, keys=None):
        self.keys = keys or {}
        self.store_calls = []

    def get_key(self, key_id: str) -> bytes:
        if key_id not in self.keys:
            # Generate a test key
            self.keys[key_id] = os.urandom(32)
        return self.keys[key_id]

    def store_key(self, key_id: str, key: bytes) -> None:
        self.keys[key_id] = key
        self.store_calls.append((key_id, key))

    def delete_key(self, key_id: str) -> bool:
        if key_id in self.keys:
            del self.keys[key_id]
            return True
        return False

    def list_keys(self):
        return list(self.keys.keys())


class TestLogReencryptionTool:
    """Test suite for LogReencryptionTool."""

    def setup_method(self):
        """Set up test fixtures."""
        self.key_provider = MockKeyProvider()
        self.tool = LogReencryptionTool(key_provider=self.key_provider, batch_size=50)

        # Create temporary directory for test files
        self.temp_dir = Path(tempfile.mkdtemp())
        self.source_file = self.temp_dir / "test_audit.log"
        self.target_file = self.temp_dir / "test_audit_reencrypted.log"

    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_test_log_entries(self, count=100, encrypted=True):
        """Create test log entries for testing."""
        entries = []

        for i in range(count):
            entry_data = {
                "timestamp": f"2024-01-01T{i:02d}:00:00Z",
                "event": f"test_event_{i}",
                "user": f"user_{i % 10}",
                "action": "login" if i % 2 == 0 else "logout",
                "ip": f"192.168.1.{i % 255}",
                "session_id": f"session_{i}"
            }

            if encrypted:
                # Create encrypted entry
                encryptor = AuditEncryption(self.key_provider.get_key("test-key"))
                encrypted_entry = encryptor.encrypt_entry(entry_data)
                entries.append(json.dumps(encrypted_entry.to_dict()))
            else:
                # Plaintext entry
                entries.append(json.dumps(entry_data))

        return entries

    def write_test_log(self, entries, file_path):
        """Write test entries to a log file."""
        with open(file_path, 'w', encoding='utf-8') as f:
            for entry in entries:
                f.write(entry + '\n')

    def test_initialization(self):
        """Test tool initialization."""
        assert self.tool.key_provider is self.key_provider
        assert self.tool.batch_size == 50
        assert self.tool.operation_id is not None
        assert len(self.tool.operation_id) == 12

    def test_create_initial_checkpoint(self):
        """Test initial checkpoint creation."""
        checkpoint = self.tool._create_initial_checkpoint(
            self.source_file, "old-key", "new-key"
        )

        assert checkpoint.operation_id == self.tool.operation_id
        assert checkpoint.phase == ReencryptionPhase.INITIALIZATION.value
        assert checkpoint.status == ReencryptionStatus.IN_PROGRESS.value
        assert checkpoint.source_file == str(self.source_file)
        assert checkpoint.retiring_key_id == "old-key"
        assert checkpoint.active_key_id == "new-key"
        assert checkpoint.total_entries == 0
        assert checkpoint.processed_entries == 0
        assert len(checkpoint.batches) == 0

    def test_count_entries(self):
        """Test entry counting."""
        entries = self.create_test_log_entries(25, encrypted=True)
        self.write_test_log(entries, self.source_file)

        count = self.tool._count_entries(self.source_file)
        assert count == 25

    def test_calculate_batch_hash(self):
        """Test batch hash calculation."""
        entries = ["entry1", "entry2", "entry3"]
        hash1 = self.tool._calculate_batch_hash(entries)

        # Same entries should produce same hash
        hash2 = self.tool._calculate_batch_hash(entries)
        assert hash1 == hash2

        # Different entries should produce different hash
        hash3 = self.tool._calculate_batch_hash(["entry4", "entry5"])
        assert hash1 != hash3

    def test_is_encrypted_entry(self):
        """Test encrypted entry detection."""
        # Encrypted entry
        encrypted_data = {
            "version": "1.1",
            "algorithm": "AES-256-GCM",
            "nonce": "test_nonce",
            "ciphertext": "test_ciphertext",
            "tag": "test_tag"
        }
        assert self.tool._is_encrypted_entry(encrypted_data) is True

        # Plaintext entry
        plaintext_data = {
            "timestamp": "2024-01-01T00:00:00Z",
            "event": "test_event"
        }
        assert self.tool._is_encrypted_entry(plaintext_data) is False

        # Incomplete encrypted entry
        incomplete_data = {
            "version": "1.1",
            "algorithm": "AES-256-GCM"
            # Missing required fields
        }
        assert self.tool._is_encrypted_entry(incomplete_data) is False

    def test_process_batch(self):
        """Test batch processing."""
        # Create test entries
        entries = self.create_test_log_entries(10, encrypted=True)

        # Create checkpoint
        checkpoint = self.tool._create_initial_checkpoint(
            self.source_file, "old-key", "new-key"
        )

        # Process batch
        success = self.tool._process_batch(
            0, entries, 0, 9,  # batch_num, entries, start_entry, end_entry
            self.key_provider.get_key("old-key"),
            self.key_provider.get_key("new-key"),
            open(self.target_file, 'w', encoding='utf-8'),
            checkpoint
        )

        assert success is True
        assert len(checkpoint.batches) == 1

        batch = checkpoint.batches[0]
        assert batch.batch_id == "batch_000000"
        assert batch.entry_count == 10
        assert batch.status == ReencryptionStatus.COMPLETED.value
        assert batch.integrity_hash is not None
        assert batch.verification_hash is not None
        assert batch.processed_at is not None

    def test_verify_integrity(self):
        """Test integrity verification."""
        # Create test data
        entries = self.create_test_log_entries(20, encrypted=True)
        self.write_test_log(entries, self.source_file)

        # Create checkpoint and process
        checkpoint = self.tool._create_initial_checkpoint(
            self.source_file, "old-key", "new-key"
        )

        # Simulate processing by manually creating batches
        with open(self.source_file, 'r', encoding='utf-8') as source_f:
            batch_entries = []
            batch_num = 0
            entry_count = 0

            for line in source_f:
                batch_entries.append(line.strip())
                entry_count += 1

                if len(batch_entries) >= 10:  # Process in batches of 10
                    with open(self.target_file, 'a', encoding='utf-8') as target_f:
                        success = self.tool._process_batch(
                            batch_num, batch_entries, batch_num * 10, entry_count - 1,
                            self.key_provider.get_key("old-key"),
                            self.key_provider.get_key("new-key"),
                            target_f, checkpoint
                        )
                        assert success

                    batch_num += 1
                    batch_entries = []

            # Process remaining entries
            if batch_entries:
                with open(self.target_file, 'a', encoding='utf-8') as target_f:
                    success = self.tool._process_batch(
                        batch_num, batch_entries, batch_num * 10, entry_count - 1,
                        self.key_provider.get_key("old-key"),
                        self.key_provider.get_key("new-key"),
                        target_f, checkpoint
                    )
                    assert success

        # Verify integrity
        integrity_ok = self.tool._verify_integrity(checkpoint, self.target_file)
        assert integrity_ok is True

    def test_perform_atomic_swap(self):
        """Test atomic file swap."""
        # Create source and target files
        self.source_file.write_text("original content\n")
        self.target_file.write_text("new content\n")

        # Perform atomic swap
        self.tool._perform_atomic_swap(self.source_file, self.target_file)

        # Verify swap occurred
        assert self.source_file.read_text() == "new content\n"
        assert not self.target_file.exists()

    def test_checkpoint_save_load(self):
        """Test checkpoint save and load."""
        checkpoint = self.tool._create_initial_checkpoint(
            self.source_file, "old-key", "new-key"
        )
        checkpoint.total_entries = 100
        checkpoint.processed_entries = 50

        # Save checkpoint
        self.tool._save_checkpoint(checkpoint)

        # Load checkpoint
        loaded = self.tool.load_checkpoint(checkpoint.operation_id)

        assert loaded is not None
        assert loaded.operation_id == checkpoint.operation_id
        assert loaded.total_entries == 100
        assert loaded.processed_entries == 50

    def test_list_checkpoints(self):
        """Test checkpoint listing."""
        # Create a checkpoint
        checkpoint = self.tool._create_initial_checkpoint(
            self.source_file, "old-key", "new-key"
        )
        self.tool._save_checkpoint(checkpoint)

        # List checkpoints
        checkpoints = self.tool.list_checkpoints()

        assert len(checkpoints) >= 1
        found = any(cp["operation_id"] == checkpoint.operation_id for cp in checkpoints)
        assert found is True

    def test_cleanup_checkpoints(self):
        """Test checkpoint cleanup."""
        # Create a checkpoint
        checkpoint = self.tool._create_initial_checkpoint(
            self.source_file, "old-key", "new-key"
        )
        self.tool._save_checkpoint(checkpoint)

        # Cleanup (should not remove recent checkpoints)
        self.tool.cleanup_checkpoints(max_age_days=0)

        # Checkpoint should still exist
        loaded = self.tool.load_checkpoint(checkpoint.operation_id)
        assert loaded is not None

    def test_reencryption_workflow(self):
        """Test complete re-encryption workflow."""
        # Create test log with encrypted entries
        entries = self.create_test_log_entries(100, encrypted=True)
        self.write_test_log(entries, self.source_file)

        # Perform re-encryption
        result = self.tool.reencrypt_log_file(
            str(self.source_file), "old-key", "new-key"
        )

        # Verify result
        assert result.success is True
        assert result.status == ReencryptionStatus.COMPLETED
        assert result.total_entries == 100
        assert result.processed_entries == 100
        assert result.failed_entries == 0
        assert result.integrity_verified is True

        # Verify target file was cleaned up (atomic swap)
        assert not self.target_file.exists()

        # Verify source file still exists and has been re-encrypted
        assert self.source_file.exists()

        # Verify we can read the re-encrypted entries
        with open(self.source_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            assert len(lines) == 100

            # Verify entries are still encrypted (with new key)
            for line in lines:
                entry_data = json.loads(line.strip())
                assert self.tool._is_encrypted_entry(entry_data)

    def test_resume_from_checkpoint(self):
        """Test resuming from checkpoint."""
        # Create test log
        entries = self.create_test_log_entries(50, encrypted=True)
        self.write_test_log(entries, self.source_file)

        # Start re-encryption
        result1 = self.tool.reencrypt_log_file(
            str(self.source_file), "old-key", "new-key"
        )

        # Should complete successfully
        assert result1.success is True

        # Create new tool and try to resume (should handle gracefully)
        new_tool = LogReencryptionTool(key_provider=self.key_provider)
        result2 = new_tool.reencrypt_log_file(
            str(self.source_file), "old-key", "new-key",
            resume_from_checkpoint=self.tool.operation_id
        )

        # Should complete (idempotent operation)
        assert result2.success is True


class TestReencryptionBatch:
    """Test ReencryptionBatch functionality."""

    def test_batch_creation(self):
        """Test batch creation and serialization."""
        batch = ReencryptionBatch(
            batch_id="test_batch",
            start_entry=0,
            end_entry=49,
            entry_count=50,
            integrity_hash="testhash",
            status=ReencryptionStatus.COMPLETED.value
        )

        assert batch.batch_id == "test_batch"
        assert batch.entry_count == 50
        assert batch.status == ReencryptionStatus.COMPLETED.value

    def test_batch_dict_conversion(self):
        """Test batch dict conversion."""
        batch = ReencryptionBatch(
            batch_id="test_batch",
            start_entry=0,
            end_entry=49,
            entry_count=50,
            integrity_hash="testhash",
            status=ReencryptionStatus.COMPLETED.value,
            processed_at="2024-01-01T00:00:00Z"
        )

        data = batch.to_dict()
        assert data["batch_id"] == "test_batch"
        assert data["entry_count"] == 50
        assert "processed_at" in data

        # Convert back
        batch2 = ReencryptionBatch.from_dict(data)
        assert batch2.batch_id == batch.batch_id
        assert batch2.processed_at == batch.processed_at


class TestReencryptionCheckpoint:
    """Test ReencryptionCheckpoint functionality."""

    def test_checkpoint_creation(self):
        """Test checkpoint creation."""
        checkpoint = ReencryptionCheckpoint(
            operation_id="test_op",
            phase=ReencryptionPhase.BATCH_PROCESSING.value,
            status=ReencryptionStatus.IN_PROGRESS.value,
            source_file="/path/to/source.log",
            target_file="/path/to/target.log",
            retiring_key_id="old-key",
            active_key_id="new-key",
            total_entries=1000,
            processed_entries=500,
            batches=[],
            start_time="2024-01-01T00:00:00Z",
            last_update="2024-01-01T01:00:00Z",
            integrity_proofs={"batch_0": "hash1"},
            metadata={"test": "value"}
        )

        assert checkpoint.operation_id == "test_op"
        assert checkpoint.total_entries == 1000
        assert checkpoint.processed_entries == 500

    def test_checkpoint_dict_conversion(self):
        """Test checkpoint dict conversion."""
        checkpoint = ReencryptionCheckpoint(
            operation_id="test_op",
            phase=ReencryptionPhase.BATCH_PROCESSING.value,
            status=ReencryptionStatus.IN_PROGRESS.value,
            source_file="/path/to/source.log",
            target_file="/path/to/target.log",
            retiring_key_id="old-key",
            active_key_id="new-key",
            total_entries=1000,
            processed_entries=500,
            batches=[],
            start_time="2024-01-01T00:00:00Z",
            last_update="2024-01-01T01:00:00Z",
            integrity_proofs={"batch_0": "hash1"},
            metadata={"test": "value"}
        )

        data = checkpoint.to_dict()
        assert data["operation_id"] == "test_op"
        assert data["total_entries"] == 1000

        # Convert back
        checkpoint2 = ReencryptionCheckpoint.from_dict(data)
        assert checkpoint2.operation_id == checkpoint.operation_id
        assert checkpoint2.total_entries == checkpoint.total_entries

    def test_add_batch(self):
        """Test adding batches to checkpoint."""
        checkpoint = ReencryptionCheckpoint(
            operation_id="test_op",
            phase=ReencryptionPhase.BATCH_PROCESSING.value,
            status=ReencryptionStatus.IN_PROGRESS.value,
            source_file="/path/to/source.log",
            target_file="",
            retiring_key_id="old-key",
            active_key_id="new-key",
            total_entries=100,
            processed_entries=0,
            batches=[],
            start_time="2024-01-01T00:00:00Z",
            last_update="2024-01-01T00:00:00Z",
            integrity_proofs={},
            metadata={}
        )

        batch = ReencryptionBatch(
            batch_id="batch_0",
            start_entry=0,
            end_entry=49,
            entry_count=50,
            integrity_hash="hash1",
            status=ReencryptionStatus.COMPLETED.value
        )

        checkpoint.add_batch(batch)

        assert len(checkpoint.batches) == 1
        assert checkpoint.processed_entries == 50
        assert checkpoint.integrity_proofs["batch_0"] == "hash1"

    def test_get_incomplete_batches(self):
        """Test getting incomplete batches."""
        checkpoint = ReencryptionCheckpoint(
            operation_id="test_op",
            phase=ReencryptionPhase.BATCH_PROCESSING.value,
            status=ReencryptionStatus.IN_PROGRESS.value,
            source_file="/path/to/source.log",
            target_file="",
            retiring_key_id="old-key",
            active_key_id="new-key",
            total_entries=100,
            processed_entries=0,
            batches=[],
            start_time="2024-01-01T00:00:00Z",
            last_update="2024-01-01T00:00:00Z",
            integrity_proofs={},
            metadata={}
        )

        # Add completed batch
        completed_batch = ReencryptionBatch(
            batch_id="batch_0",
            start_entry=0,
            end_entry=49,
            entry_count=50,
            integrity_hash="hash1",
            status=ReencryptionStatus.COMPLETED.value
        )
        checkpoint.add_batch(completed_batch)

        # Add incomplete batch
        incomplete_batch = ReencryptionBatch(
            batch_id="batch_1",
            start_entry=50,
            end_entry=99,
            entry_count=50,
            integrity_hash="hash2",
            status=ReencryptionStatus.IN_PROGRESS.value
        )
        checkpoint.batches.append(incomplete_batch)

        incomplete = checkpoint.get_incomplete_batches()
        assert len(incomplete) == 1
        assert incomplete[0].batch_id == "batch_1"


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_reencrypt_audit_log_function(self):
        """Test reencrypt_audit_log convenience function."""
        with patch('lazyscan.security.log_reencryption_tool.LogReencryptionTool') as mock_tool_class:
            mock_tool = MagicMock()
            mock_tool.reencrypt_log_file.return_value = ReencryptionResult(
                success=True,
                status=ReencryptionStatus.COMPLETED,
                operation_id="test_op",
                total_entries=100,
                processed_entries=100,
                failed_entries=0,
                batches_processed=2,
                integrity_verified=True,
                duration_seconds=10.0,
                error_summary={}
            )
            mock_tool_class.return_value = mock_tool

            result = reencrypt_audit_log("source.log", "old-key", "new-key")

            assert result.success is True
            mock_tool_class.assert_called_once()
            mock_tool.reencrypt_log_file.assert_called_once_with(
                "source.log", "old-key", "new-key", None
            )

    def test_get_reencryption_checkpoints_function(self):
        """Test get_reencryption_checkpoints convenience function."""
        with patch('lazyscan.security.log_reencryption_tool.LogReencryptionTool') as mock_tool_class:
            mock_tool = MagicMock()
            mock_tool.list_checkpoints.return_value = [{"operation_id": "test"}]
            mock_tool_class.return_value = mock_tool

            checkpoints = get_reencryption_checkpoints()

            assert len(checkpoints) == 1
            mock_tool_class.assert_called_once()
            mock_tool.list_checkpoints.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])</content>
</xai:function_call">Writing to /Users/vinayvidyasagar/Dev/LazyScan/tests/security/test_log_reencryption_tool.py