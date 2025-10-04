#!/usr/bin/env python3
"""
Comprehensive tests for AES-256-GCM audit encryption functionality.

Subtask 9.6.1: Unit-level encryption/decryption round-trip coverage
- Deterministic test fixtures for keys and nonces
- Round-trip encryption/decryption tests
- Edge cases: zero-length payloads, maximum allowed payload size, multi-block entries
- Ciphertext integrity validation
- Deterministic metadata validation
"""

import pytest
import json
import base64
import hashlib
import os
from unittest.mock import Mock, patch
from datetime import datetime, timezone

# Test the encryption functionality
try:
    from lazyscan.security.audit_encryption import (
        AuditEncryption,
        AuditEncryptionError,
        AuditDecryptionError,
        EncryptedAuditEntry,
    )
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False


# Deterministic test fixtures for Subtask 9.6.1
@pytest.fixture
def deterministic_key():
    """Deterministic AES-256 key for reproducible testing."""
    # Use SHA-256 of a fixed string to generate deterministic key
    return hashlib.sha256(b"LazyScan-Test-Key-Fixture-v1.1").digest()


@pytest.fixture
def deterministic_nonce():
    """Deterministic 96-bit nonce for reproducible testing."""
    # Fixed 12-byte nonce for deterministic testing
    return b"test_nonce12"  # Exactly 12 bytes


@pytest.fixture
def deterministic_encryptor(deterministic_key):
    """AuditEncryption instance with deterministic key."""
    if ENCRYPTION_AVAILABLE:
        return AuditEncryption(deterministic_key)
    return None


@pytest.fixture
def mock_deterministic_nonce(monkeypatch, deterministic_nonce):
    """Mock os.urandom to return deterministic nonce."""
    def mock_urandom(size):
        if size == 12:  # Nonce size
            return deterministic_nonce
        return os.urandom(size)  # Real random for other uses

    monkeypatch.setattr('os.urandom', mock_urandom)


@pytest.mark.skipif(not ENCRYPTION_AVAILABLE, reason="Cryptography not available")
class TestDeterministicRoundTripCoverage:
    """Subtask 9.6.1: Comprehensive deterministic round-trip testing."""

    def test_deterministic_encrypt_decrypt_roundtrip(self, deterministic_encryptor, mock_deterministic_nonce):
        """Test deterministic encrypt/decrypt roundtrip with fixed key and nonce."""
        if not deterministic_encryptor:
            pytest.skip("Encryption not available")

        test_data = {
            "event_type": "deterministic_test",
            "message": "Deterministic test message",
            "timestamp": "2025-01-01T00:00:00Z",
            "details": {"test": "deterministic_data", "sequence": 12345}
        }

        # Encrypt with deterministic fixtures
        encrypted = deterministic_encryptor.encrypt_entry(test_data)
        assert isinstance(encrypted, EncryptedAuditEntry)
        assert encrypted.algorithm == "AES-256-GCM"
        assert encrypted.version == "1.1"

        # Verify deterministic nonce
        expected_nonce = base64.b64encode(b"test_nonce12").decode('ascii')
        assert encrypted.nonce == expected_nonce

        # Decrypt and verify roundtrip
        decrypted = deterministic_encryptor.decrypt_entry(encrypted)
        assert decrypted == test_data

    def test_zero_length_payload_roundtrip(self, deterministic_encryptor):
        """Test encryption/decryption of zero-length payload (empty dict)."""
        if not deterministic_encryptor:
            pytest.skip("Encryption not available")

        test_data = {}

        # Encrypt
        encrypted = deterministic_encryptor.encrypt_entry(test_data)

        # Decrypt
        decrypted = deterministic_encryptor.decrypt_entry(encrypted)

        # Verify roundtrip
        assert decrypted == test_data

    def test_maximum_payload_size_roundtrip(self, deterministic_encryptor):
        """Test encryption/decryption of maximum allowed payload size."""
        if not deterministic_encryptor:
            pytest.skip("Encryption not available")

        # Create a large payload (approximately 1MB)
        large_data = "x" * (1024 * 1024)  # 1MB string
        test_data = {
            "event_type": "large_payload_test",
            "large_field": large_data,
            "metadata": {"size": len(large_data), "type": "stress_test"}
        }

        # Encrypt
        encrypted = deterministic_encryptor.encrypt_entry(test_data)

        # Decrypt
        decrypted = deterministic_encryptor.decrypt_entry(encrypted)

        # Verify roundtrip
        assert decrypted == test_data
        assert len(decrypted["large_field"]) == len(large_data)

    def test_multi_block_payload_roundtrip(self, deterministic_encryptor):
        """Test encryption/decryption of multi-block payload (>16KB)."""
        if not deterministic_encryptor:
            pytest.skip("Encryption not available")

        # Create multi-block payload (AES block size is 16 bytes, test >16KB)
        block_size = 16 * 1024  # 16KB
        large_data = "A" * block_size + "B" * block_size + "C" * block_size
        test_data = {
            "event_type": "multi_block_test",
            "data": large_data,
            "blocks": 3,
            "block_size": block_size
        }

        # Encrypt
        encrypted = deterministic_encryptor.encrypt_entry(test_data)

        # Decrypt
        decrypted = deterministic_encryptor.decrypt_entry(encrypted)

        # Verify roundtrip
        assert decrypted == test_data
        assert len(decrypted["data"]) == len(large_data)

    def test_deterministic_metadata_validation(self, deterministic_encryptor, mock_deterministic_nonce):
        """Test deterministic metadata validation in encrypted entries."""
        if not deterministic_encryptor:
            pytest.skip("Encryption not available")

        test_data = {"test": "metadata_validation"}

        # Encrypt
        encrypted = deterministic_encryptor.encrypt_entry(test_data)

        # Validate deterministic metadata
        assert encrypted.version == "1.1"
        assert encrypted.algorithm == "AES-256-GCM"
        assert encrypted.nonce == base64.b64encode(b"test_nonce12").decode('ascii')
        assert encrypted.associated_data == base64.b64encode(AuditEncryption.ASSOCIATED_DATA).decode('ascii')

        # Validate base64 encoding/decoding
        nonce_bytes = base64.b64decode(encrypted.nonce)
        ciphertext_bytes = base64.b64decode(encrypted.ciphertext)
        tag_bytes = base64.b64decode(encrypted.tag)
        aad_bytes = base64.b64decode(encrypted.associated_data)

        assert len(nonce_bytes) == 12  # 96 bits
        assert len(tag_bytes) == 16   # GCM tag
        assert len(ciphertext_bytes) > 0
        assert aad_bytes == AuditEncryption.ASSOCIATED_DATA

    def test_ciphertext_integrity_validation(self, deterministic_encryptor):
        """Test ciphertext integrity validation and tamper detection."""
        if not deterministic_encryptor:
            pytest.skip("Encryption not available")

        test_data = {"integrity": "test"}

        # Encrypt
        encrypted = deterministic_encryptor.encrypt_entry(test_data)

        # Test 1: Valid decryption should work
        decrypted = deterministic_encryptor.decrypt_entry(encrypted)
        assert decrypted == test_data

        # Test 2: Tampered ciphertext should fail
        tampered = encrypted.to_dict()
        tampered["ciphertext"] = base64.b64encode(b"tampered_data").decode('ascii')
        tampered_entry = EncryptedAuditEntry.from_dict(tampered)

        with pytest.raises(AuditDecryptionError, match="Integrity check failed"):
            deterministic_encryptor.decrypt_entry(tampered_entry)

        # Test 3: Tampered tag should fail
        tampered = encrypted.to_dict()
        tampered["tag"] = base64.b64encode(b"bad_tag_16_bytes").decode('ascii')  # 16 bytes
        tampered_entry = EncryptedAuditEntry.from_dict(tampered)

        with pytest.raises(AuditDecryptionError, match="Integrity check failed"):
            deterministic_encryptor.decrypt_entry(tampered_entry)

        # Test 4: Tampered associated data should fail
        tampered = encrypted.to_dict()
        tampered["associated_data"] = base64.b64encode(b"wrong_aad").decode('ascii')
        tampered_entry = EncryptedAuditEntry.from_dict(tampered)

        with pytest.raises(AuditDecryptionError, match="Integrity check failed"):
            deterministic_encryptor.decrypt_entry(tampered_entry)

    def test_edge_case_payloads_roundtrip(self, deterministic_encryptor):
        """Test various edge case payloads for roundtrip coverage."""
        if not deterministic_encryptor:
            pytest.skip("Encryption not available")

        edge_cases = [
            # Empty dict
            {},
            # Single key-value
            {"key": "value"},
            # Nested structures
            {"nested": {"deep": {"structure": [1, 2, 3]}}},
            # Unicode content
            {"unicode": "🚀 测试 αβγ"},
            # Large numbers
            {"big_number": 2**63 - 1},
            # Boolean and None values
            {"bool": True, "none": None, "false": False},
            # Empty strings and arrays
            {"empty_string": "", "empty_array": []},
        ]

        for i, test_data in enumerate(edge_cases):
            # Encrypt
            encrypted = deterministic_encryptor.encrypt_entry(test_data)

            # Decrypt
            decrypted = deterministic_encryptor.decrypt_entry(encrypted)

            # Verify roundtrip
            assert decrypted == test_data, f"Failed roundtrip for edge case {i}: {test_data}"

    def test_deterministic_key_consistency(self, deterministic_key, deterministic_encryptor, mock_deterministic_nonce):
        """Test that deterministic key produces consistent results."""
        if not deterministic_encryptor:
            pytest.skip("Encryption not available")

        test_data = {"consistency": "test"}

        # Encrypt multiple times with same key and nonce
        encrypted1 = deterministic_encryptor.encrypt_entry(test_data)
        encrypted2 = deterministic_encryptor.encrypt_entry(test_data)

        # Results should be identical due to deterministic nonce
        assert encrypted1.nonce == encrypted2.nonce
        assert encrypted1.ciphertext == encrypted2.ciphertext
        assert encrypted1.tag == encrypted2.tag

        # Both should decrypt to same data
        decrypted1 = deterministic_encryptor.decrypt_entry(encrypted1)
        decrypted2 = deterministic_encryptor.decrypt_entry(encrypted2)

        assert decrypted1 == test_data
        assert decrypted2 == test_data


if __name__ == "__main__":
    pytest.main([__file__])