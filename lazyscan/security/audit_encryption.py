#!/usr/bin/env python3
"""
AES-256-GCM Encryption Utilities for Audit Logging

This module provides AES-256-GCM encryption and decryption utilities
for securing audit log entries with authenticated encryption.
"""

import os
import base64
import json
import hashlib
from typing import Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidTag

from ..core.errors import SecurityPolicyError
from ..core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class EncryptedAuditEntry:
    """Represents an encrypted audit log entry."""

    version: str = "1.1"  # Log format version
    algorithm: str = "AES-256-GCM"
    timestamp: str = ""  # ISO format timestamp
    nonce: str = ""  # Base64 encoded 96-bit nonce
    ciphertext: str = ""  # Base64 encoded encrypted data
    tag: str = ""  # Base64 encoded authentication tag
    associated_data: Optional[str] = None  # Base64 encoded associated data

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EncryptedAuditEntry":
        """Create from dictionary."""
        return cls(**data)


class AuditEncryptionError(SecurityPolicyError):
    """Base exception for audit encryption operations."""
    pass


class AuditDecryptionError(AuditEncryptionError):
    """Raised when decryption fails."""
    pass


class AuditEncryption:
    """
    AES-256-GCM encryption/decryption for audit log entries.

    Provides authenticated encryption with associated data for integrity
    and authenticity verification.
    """

    # Key size for AES-256
    KEY_SIZE = 32  # 256 bits

    # Nonce size for GCM (96 bits = 12 bytes)
    NONCE_SIZE = 12

    # Associated data for integrity
    ASSOCIATED_DATA = b"LazyScan-Audit-Entry-v1.1"

    def __init__(self, key: bytes):
        """
        Initialize with encryption key.

        Args:
            key: 32-byte AES-256 key

        Raises:
            AuditEncryptionError: If key is invalid
        """
        if not isinstance(key, bytes):
            raise AuditEncryptionError("Key must be bytes")
        if len(key) != self.KEY_SIZE:
            raise AuditEncryptionError(f"Key must be {self.KEY_SIZE} bytes, got {len(key)}")

        self.key = key
        self.backend = default_backend()

    @classmethod
    def generate_key(cls) -> bytes:
        """Generate a new random AES-256 key."""
        return os.urandom(cls.KEY_SIZE)

    def encrypt_entry(self, entry_data: Dict[str, Any]) -> EncryptedAuditEntry:
        """
        Encrypt an audit log entry.

        Args:
            entry_data: The audit entry data to encrypt

        Returns:
            EncryptedAuditEntry with encrypted data

        Raises:
            AuditEncryptionError: If encryption fails
        """
        try:
            # Generate fresh nonce for this entry
            nonce = os.urandom(self.NONCE_SIZE)

            # Serialize entry data to JSON
            plaintext = json.dumps(entry_data, sort_keys=True, ensure_ascii=False).encode('utf-8')

            # Create cipher
            cipher = Cipher(
                algorithms.AES(self.key),
                modes.GCM(nonce),
                backend=self.backend
            )
            encryptor = cipher.encryptor()

            # Add associated data for integrity
            encryptor.authenticate_additional_data(self.ASSOCIATED_DATA)

            # Encrypt the data
            ciphertext = encryptor.update(plaintext) + encryptor.finalize()

            # Get authentication tag
            tag = encryptor.tag

            # Create encrypted entry
            encrypted_entry = EncryptedAuditEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                nonce=base64.b64encode(nonce).decode('ascii'),
                ciphertext=base64.b64encode(ciphertext).decode('ascii'),
                tag=base64.b64encode(tag).decode('ascii'),
                associated_data=base64.b64encode(self.ASSOCIATED_DATA).decode('ascii')
            )

            logger.debug("Successfully encrypted audit entry",
                        entry_size=len(plaintext),
                        ciphertext_size=len(ciphertext))

            return encrypted_entry

        except Exception as e:
            logger.error(f"Failed to encrypt audit entry: {e}")
            raise AuditEncryptionError(f"Encryption failed: {e}")

    def decrypt_entry(self, encrypted_entry: EncryptedAuditEntry) -> Dict[str, Any]:
        """
        Decrypt an encrypted audit log entry.

        Args:
            encrypted_entry: The encrypted entry to decrypt

        Returns:
            Decrypted entry data as dictionary

        Raises:
            AuditDecryptionError: If decryption fails or integrity check fails
        """
        try:
            # Decode base64 components
            nonce = base64.b64decode(encrypted_entry.nonce)
            ciphertext = base64.b64decode(encrypted_entry.ciphertext)
            tag = base64.b64decode(encrypted_entry.tag)

            # Verify nonce size
            if len(nonce) != self.NONCE_SIZE:
                raise AuditDecryptionError(f"Invalid nonce size: {len(nonce)}")

            # Decode associated data
            associated_data = base64.b64decode(encrypted_entry.associated_data) if encrypted_entry.associated_data else self.ASSOCIATED_DATA

            # Create cipher for decryption
            cipher = Cipher(
                algorithms.AES(self.key),
                modes.GCM(nonce, tag),
                backend=self.backend
            )
            decryptor = cipher.decryptor()

            # Add associated data for integrity verification
            decryptor.authenticate_additional_data(associated_data)

            # Decrypt the data
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()

            # Parse JSON
            entry_data = json.loads(plaintext.decode('utf-8'))

            logger.debug("Successfully decrypted audit entry",
                        ciphertext_size=len(ciphertext),
                        plaintext_size=len(plaintext))

            return entry_data

        except InvalidTag:
            logger.warning("Authentication tag verification failed - possible tampering")
            raise AuditDecryptionError("Integrity check failed - entry may be tampered with")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse decrypted JSON: {e}")
            raise AuditDecryptionError(f"Invalid decrypted data: {e}")
        except Exception as e:
            logger.error(f"Failed to decrypt audit entry: {e}")
            raise AuditDecryptionError(f"Decryption failed: {e}")

    def is_encrypted_entry(self, data: Union[str, Dict[str, Any]]) -> bool:
        """
        Check if data represents an encrypted audit entry.

        Args:
            data: Data to check (string or dict)

        Returns:
            True if this appears to be an encrypted entry
        """
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                return False

        if not isinstance(data, dict):
            return False

        # Check for required encryption fields
        required_fields = ['version', 'algorithm', 'nonce', 'ciphertext', 'tag']
        return all(field in data for field in required_fields) and data.get('algorithm') == 'AES-256-GCM'

    def create_legacy_entry(self, entry_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a legacy plaintext entry for backward compatibility.

        Args:
            entry_data: The audit entry data

        Returns:
            Legacy format entry
        """
        # Add legacy marker
        legacy_entry = entry_data.copy()
        legacy_entry['_format'] = 'legacy-plaintext'
        legacy_entry['_encrypted'] = False
        return legacy_entry


def get_audit_key_from_provider(key_provider, key_id: str = "lazyscan-audit-key") -> bytes:
    """
    Retrieve audit encryption key from key provider.

    Args:
        key_provider: KeyProvider instance
        key_id: Key identifier

    Returns:
        32-byte AES key

    Raises:
        AuditEncryptionError: If key retrieval fails
    """
    try:
        key = key_provider.get_key(key_id)

        # Ensure key is correct size
        if len(key) != AuditEncryption.KEY_SIZE:
            # If key is wrong size, derive a proper key from it
            key = hashlib.sha256(key).digest()

        return key

    except Exception as e:
        logger.error(f"Failed to retrieve audit key '{key_id}': {e}")
        raise AuditEncryptionError(f"Key retrieval failed: {e}")


def ensure_audit_key(key_provider, key_id: str = "lazyscan-audit-key") -> bytes:
    """
    Ensure an audit encryption key exists, creating one if necessary.

    Args:
        key_provider: KeyProvider instance
        key_id: Key identifier

    Returns:
        32-byte AES key

    Raises:
        AuditEncryptionError: If key operations fail
    """
    try:
        # Try to get existing key
        try:
            return get_audit_key_from_provider(key_provider, key_id)
        except Exception:
            # Key doesn't exist, create a new one
            logger.info(f"Creating new audit encryption key: {key_id}")
            new_key = AuditEncryption.generate_key()
            key_provider.store_key(key_id, new_key)
            return new_key

    except Exception as e:
        logger.error(f"Failed to ensure audit key '{key_id}': {e}")
        raise AuditEncryptionError(f"Key setup failed: {e}")


__all__ = [
    "AuditEncryption",
    "AuditEncryptionError", 
    "AuditDecryptionError",
    "EncryptedAuditEntry",
    "get_audit_key_from_provider",
    "ensure_audit_key",
]