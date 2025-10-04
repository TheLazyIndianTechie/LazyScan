#!/usr/bin/env python3
"""
Tests for RecoveryDecryptor functionality.

This module provides comprehensive tests for the audit log recovery decryption
pipeline, including key rotation scenarios and error handling.
"""

import os
import json
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from datetime import datetime, timezone

# Import the modules to test
try:
    from lazyscan.security.recovery_decryptor import (
        RecoveryDecryptor,
        RecoveryDecryptorError,
        RecoveryResult,
        RecoveryMetrics,
        RecoveryStatus,
        RecoveryError,
        KeyRotationManager,
        recover_audit_logs,
        validate_audit_log_integrity,
    )
    from lazyscan.security.audit_encryption import (
        AuditEncryption,
        EncryptedAuditEntry,
        AuditEncryptionError,
    )
    from lazyscan.security.key_providers import KeyProvider, KeyProviderError
    ENCRYPTION_AVAILABLE = True
except ImportError:
    # Mock the imports for testing when dependencies are not available
    ENCRYPTION_AVAILABLE = False


@unittest.skipUnless(ENCRYPTION_AVAILABLE, "Encryption dependencies not available")
class TestRecoveryDecryptor(unittest.TestCase):
    """Test cases for RecoveryDecryptor functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_key = AuditEncryption.generate_key()
        self.mock_key_provider = Mock(spec=KeyProvider)

        # Mock key provider to return our test key
        self.mock_key_provider.get_key.return_value = self.test_key

        # Create test audit entries
        self.audit_encryptor = AuditEncryption(self.test_key)
        self.test_entries = [
            {"event_type": "startup", "message": "Application started", "user": "test"},
            {"event_type": "scan_complete", "message": "Scan finished", "files_found": 100},
            {"event_type": "error", "message": "Test error", "error_code": "TEST_001"},
        ]

    def _create_encrypted_log_file(self, entries: list) -> str:
        """Create a temporary encrypted log file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            for entry in entries:
                encrypted_entry = self.audit_encryptor.encrypt_entry(entry)
                json.dump(encrypted_entry.to_dict(), f)
                f.write('\n')
            temp_file = f.name

        return temp_file

    def _create_plaintext_log_file(self, entries: list) -> str:
        """Create a temporary plaintext log file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            for entry in entries:
                entry['_encrypted'] = False
                json.dump(entry, f)
                f.write('\n')
            temp_file = f.name

        return temp_file

    def tearDown(self):
        """Clean up test files."""
        # Clean up any temp files created during tests
        pass

    def test_recovery_decryptor_initialization(self):
        """Test RecoveryDecryptor initialization."""
        decryptor = RecoveryDecryptor(self.mock_key_provider)

        self.assertIsNotNone(decryptor.session_id)
        self.assertIsNotNone(decryptor.key_provider)
        self.assertIsNotNone(decryptor.key_rotation_manager)

    def test_successful_recovery_from_encrypted_file(self):
        """Test successful recovery from encrypted log file."""
        # Create encrypted log file
        encrypted_file = self._create_encrypted_log_file(self.test_entries)

        try:
            decryptor = RecoveryDecryptor(self.mock_key_provider)
            result = decryptor.recover_from_file(encrypted_file)

            # Verify results
            self.assertTrue(result.success)
            self.assertEqual(result.status, RecoveryStatus.COMPLETED)
            self.assertEqual(len(result.decrypted_entries), len(self.test_entries))
            self.assertEqual(result.metrics.total_entries, len(self.test_entries))
            self.assertEqual(result.metrics.decrypted_entries, len(self.test_entries))
            self.assertEqual(result.metrics.failed_entries, 0)

            # Verify decrypted content
            for i, decrypted in enumerate(result.decrypted_entries):
                self.assertEqual(decrypted['event_type'], self.test_entries[i]['event_type'])
                self.assertEqual(decrypted['message'], self.test_entries[i]['message'])

        finally:
            os.unlink(encrypted_file)

    def test_recovery_from_plaintext_file(self):
        """Test recovery from plaintext log file."""
        # Create plaintext log file
        plaintext_file = self._create_plaintext_log_file(self.test_entries)

        try:
            decryptor = RecoveryDecryptor(self.mock_key_provider)
            result = decryptor.recover_from_file(plaintext_file)

            # Verify results
            self.assertTrue(result.success)
            self.assertEqual(result.status, RecoveryStatus.COMPLETED)
            self.assertEqual(len(result.decrypted_entries), len(self.test_entries))

        finally:
            os.unlink(plaintext_file)

    def test_recovery_with_corrupted_entries(self):
        """Test recovery with some corrupted entries."""
        # Create log file with mix of valid and invalid entries
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            # Valid encrypted entry
            encrypted_entry = self.audit_encryptor.encrypt_entry(self.test_entries[0])
            json.dump(encrypted_entry.to_dict(), f)
            f.write('\n')

            # Invalid JSON
            f.write('{"invalid": json content\n')

            # Another valid entry
            encrypted_entry = self.audit_encryptor.encrypt_entry(self.test_entries[1])
            json.dump(encrypted_entry.to_dict(), f)
            f.write('\n')

            temp_file = f.name

        try:
            decryptor = RecoveryDecryptor(self.mock_key_provider)
            result = decryptor.recover_from_file(temp_file)

            # Should have partial success
            self.assertTrue(result.success)
            self.assertEqual(result.status, RecoveryStatus.PARTIAL)
            self.assertEqual(result.metrics.total_entries, 3)  # 2 valid + 1 invalid
            self.assertEqual(result.metrics.decrypted_entries, 2)
            self.assertEqual(result.metrics.failed_entries, 1)

        finally:
            os.unlink(temp_file)

    def test_recovery_to_file(self):
        """Test recovery with output to file."""
        # Create encrypted log file
        encrypted_file = self._create_encrypted_log_file(self.test_entries)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as output_f:
            output_file = output_f.name

        try:
            decryptor = RecoveryDecryptor(self.mock_key_provider)
            result = decryptor.recover_to_file(encrypted_file, output_file)

            # Verify results
            self.assertTrue(result.success)
            self.assertEqual(result.status, RecoveryStatus.COMPLETED)

            # Verify output file contents
            with open(output_file, 'r') as f:
                lines = f.readlines()
                self.assertEqual(len(lines), len(self.test_entries))

                for i, line in enumerate(lines):
                    entry = json.loads(line.strip())
                    self.assertEqual(entry['event_type'], self.test_entries[i]['event_type'])

        finally:
            os.unlink(encrypted_file)
            os.unlink(output_file)

    def test_key_rotation_manager(self):
        """Test KeyRotationManager functionality."""
        key_manager = KeyRotationManager(self.mock_key_provider)

        # Test active key retrieval
        active_key = key_manager.get_active_key()
        self.assertEqual(active_key, self.test_key)

        # Test key caching
        active_key2 = key_manager.get_active_key()
        self.assertEqual(active_key, active_key2)
        self.assertEqual(self.mock_key_provider.get_key.call_count, 1)  # Should be cached

    def test_validate_log_integrity(self):
        """Test log integrity validation."""
        # Create encrypted log file
        encrypted_file = self._create_encrypted_log_file(self.test_entries)

        try:
            decryptor = RecoveryDecryptor(self.mock_key_provider)
            validation = decryptor.validate_log_integrity(encrypted_file)

            self.assertEqual(validation['total_entries'], len(self.test_entries))
            self.assertEqual(validation['valid_entries'], len(self.test_entries))
            self.assertEqual(validation['invalid_entries'], 0)
            self.assertEqual(validation['integrity_score'], 100.0)

        finally:
            os.unlink(encrypted_file)

    def test_metrics_calculation(self):
        """Test metrics calculation."""
        metrics = RecoveryMetrics()
        metrics.total_entries = 10
        metrics.decrypted_entries = 8
        metrics.failed_entries = 2
        metrics.start_time = datetime.now(timezone.utc).isoformat()
        metrics.end_time = (datetime.now(timezone.utc).replace(second=1)).isoformat()

        metrics.finalize()

        self.assertAlmostEqual(metrics.throughput_entries_per_second, 10.0, places=1)
        self.assertGreater(metrics.duration_seconds, 0)

    def test_error_recording(self):
        """Test error recording in metrics."""
        metrics = RecoveryMetrics()

        metrics.record_error(RecoveryError.DECRYPTION_FAILED)
        metrics.record_error(RecoveryError.DECRYPTION_FAILED)
        metrics.record_error(RecoveryError.INTEGRITY_CHECK_FAILED)

        self.assertEqual(metrics.error_counts[RecoveryError.DECRYPTION_FAILED.value], 2)
        self.assertEqual(metrics.error_counts[RecoveryError.INTEGRITY_CHECK_FAILED.value], 1)

    def test_key_version_recording(self):
        """Test key version recording."""
        metrics = RecoveryMetrics()

        metrics.record_key_version("current")
        metrics.record_key_version("v1.0")
        metrics.record_key_version("current")  # Duplicate

        self.assertEqual(len(metrics.key_versions_used), 2)
        self.assertIn("current", metrics.key_versions_used)
        self.assertIn("v1.0", metrics.key_versions_used)

    def test_convenience_functions(self):
        """Test convenience functions."""
        # Create encrypted log file
        encrypted_file = self._create_encrypted_log_file(self.test_entries)

        try:
            # Test recover_audit_logs
            result = recover_audit_logs(encrypted_file, key_provider=self.mock_key_provider)
            self.assertTrue(result.success)
            self.assertEqual(len(result.decrypted_entries), len(self.test_entries))

            # Test validate_audit_log_integrity
            validation = validate_audit_log_integrity(encrypted_file, key_provider=self.mock_key_provider)
            self.assertEqual(validation['total_entries'], len(self.test_entries))
            self.assertEqual(validation['integrity_score'], 100.0)

        finally:
            os.unlink(encrypted_file)

    def test_missing_file_handling(self):
        """Test handling of missing input files."""
        decryptor = RecoveryDecryptor(self.mock_key_provider)

        with self.assertRaises(RecoveryDecryptorError):
            decryptor.recover_from_file("/nonexistent/file.jsonl")


class TestRecoveryDecryptorErrors(unittest.TestCase):
    """Test error handling in RecoveryDecryptor."""

    @unittest.skipUnless(ENCRYPTION_AVAILABLE, "Encryption dependencies not available")
    def setUp(self):
        """Set up test fixtures."""
        self.mock_key_provider = Mock(spec=KeyProvider)
        self.mock_key_provider.get_key.side_effect = KeyProviderError("Key unavailable")

    def test_key_unavailable_error(self):
        """Test handling of unavailable keys."""
        decryptor = RecoveryDecryptor(self.mock_key_provider)

        # Create a dummy file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"test": "data"}\n')
            temp_file = f.name

        try:
            result = decryptor.recover_from_file(temp_file)

            # Should fail due to key unavailability
            self.assertFalse(result.success)
            self.assertEqual(result.status, RecoveryStatus.FAILED)

        finally:
            os.unlink(temp_file)


if __name__ == '__main__':
    unittest.main()
