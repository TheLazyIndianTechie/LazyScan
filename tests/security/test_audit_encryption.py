#!/usr/bin/env python3
"""
Tests for AES-256-GCM audit encryption functionality.

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
from unittest.mock import Mock, patch, mock_open
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
class TestAuditEncryption:
    """Test AES-256-GCM audit encryption."""

    def test_generate_key(self):
        """Test key generation."""
        key = AuditEncryption.generate_key()
        assert len(key) == 32  # AES-256
        assert isinstance(key, bytes)

    # Subtask 9.6.1: Deterministic round-trip coverage
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
        tampered["tag"] = base64.b64encode(b"bad_tag").decode('ascii')
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

    def test_encrypt_decrypt_roundtrip(self):
        """Test full encrypt/decrypt roundtrip."""
        key = AuditEncryption.generate_key()
        encryptor = AuditEncryption(key)

        test_data = {
            "event_type": "test_event",
            "message": "Test message",
            "timestamp": "2023-01-01T00:00:00Z",
            "details": {"test": "data"}
        }

        # Encrypt
        encrypted = encryptor.encrypt_entry(test_data)
        assert isinstance(encrypted, EncryptedAuditEntry)
        assert encrypted.algorithm == "AES-256-GCM"
        assert encrypted.version == "1.1"

        # Verify base64 encoding
        assert encrypted.nonce
        assert encrypted.ciphertext
        assert encrypted.tag
        assert encrypted.associated_data

        # Verify base64 decode works
        nonce_bytes = base64.b64decode(encrypted.nonce)
        ciphertext_bytes = base64.b64decode(encrypted.ciphertext)
        tag_bytes = base64.b64decode(encrypted.tag)

        assert len(nonce_bytes) == 12  # 96 bits
        assert len(tag_bytes) == 16  # GCM tag
        assert len(ciphertext_bytes) > 0

        # Decrypt
        decrypted = encryptor.decrypt_entry(encrypted)

        # Verify roundtrip
        assert decrypted == test_data

    def test_different_nonces(self):
        """Test that different encryptions use different nonces."""
        key = AuditEncryption.generate_key()
        encryptor = AuditEncryption(key)

        test_data = {"test": "data"}

        # Encrypt twice
        encrypted1 = encryptor.encrypt_entry(test_data)
        encrypted2 = encryptor.encrypt_entry(test_data)

        # Nonces should be different
        assert encrypted1.nonce != encrypted2.nonce

        # But both should decrypt correctly
        decrypted1 = encryptor.decrypt_entry(encrypted1)
        decrypted2 = encryptor.decrypt_entry(encrypted2)

        assert decrypted1 == test_data
        assert decrypted2 == test_data

    def test_tampering_detection(self):
        """Test that tampering is detected."""
        key = AuditEncryption.generate_key()
        encryptor = AuditEncryption(key)

        test_data = {"test": "data"}
        encrypted = encryptor.encrypt_entry(test_data)

        # Tamper with ciphertext
        tampered = encrypted.to_dict()
        tampered["ciphertext"] = base64.b64encode(b"tampered").decode('ascii')
        tampered_entry = EncryptedAuditEntry.from_dict(tampered)

        # Decryption should fail
        with pytest.raises(AuditDecryptionError):
            encryptor.decrypt_entry(tampered_entry)

    def test_invalid_key_size(self):
        """Test invalid key sizes are rejected."""
        with pytest.raises(AuditEncryptionError):
            AuditEncryption(b"short_key")

        with pytest.raises(AuditEncryptionError):
            AuditEncryption(b"too_long_key" * 10)

    def test_is_encrypted_entry_detection(self):
        """Test detection of encrypted vs plaintext entries."""
        key = AuditEncryption.generate_key()
        encryptor = AuditEncryption(key)

        # Test encrypted entry
        test_data = {"test": "data"}
        encrypted = encryptor.encrypt_entry(test_data)
        encrypted_dict = encrypted.to_dict()

        assert encryptor.is_encrypted_entry(encrypted_dict)
        assert encryptor.is_encrypted_entry(json.dumps(encrypted_dict))

        # Test plaintext entry
        plaintext = {"event_type": "test", "message": "test"}
        assert not encryptor.is_encrypted_entry(plaintext)
        assert not encryptor.is_encrypted_entry(json.dumps(plaintext))

    def test_legacy_entry_creation(self):
        """Test legacy plaintext entry creation."""
        key = AuditEncryption.generate_key()
        encryptor = AuditEncryption(key)

        test_data = {"test": "data"}
        legacy = encryptor.create_legacy_entry(test_data)

        assert legacy["_format"] == "legacy-plaintext"
        assert legacy["_encrypted"] == False
        assert legacy["test"] == "data"


@pytest.mark.skipif(not ENCRYPTION_AVAILABLE, reason="Cryptography not available")
class TestEncryptedAuditEntry:
    """Test EncryptedAuditEntry dataclass."""

    def test_to_from_dict(self):
        """Test serialization/deserialization."""
        entry = EncryptedAuditEntry(
            version="1.1",
            algorithm="AES-256-GCM",
            timestamp="2023-01-01T00:00:00Z",
            nonce="nonce123",
            ciphertext="ciphertext123",
            tag="tag123",
            associated_data="aad123"
        )

        # Convert to dict
        entry_dict = entry.to_dict()
        assert entry_dict["version"] == "1.1"
        assert entry_dict["algorithm"] == "AES-256-GCM"
        assert "associated_data" in entry_dict

        # Convert back
        restored = EncryptedAuditEntry.from_dict(entry_dict)
        assert restored.version == entry.version
        assert restored.nonce == entry.nonce

    def test_optional_fields(self):
        """Test optional associated_data field."""
        entry = EncryptedAuditEntry(
            nonce="nonce123",
            ciphertext="ciphertext123",
            tag="tag123"
        )

        entry_dict = entry.to_dict()
        # associated_data should not be in dict when None
        assert "associated_data" not in entry_dict

        restored = EncryptedAuditEntry.from_dict(entry_dict)
        assert restored.associated_data is None


if __name__ == "__main__":
    pytest.main([__file__])</content>
</xai:function_call">The file has been created successfully.