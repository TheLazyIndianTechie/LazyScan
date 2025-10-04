#!/usr/bin/env python3
"""
Windows Credential Manager Key Provider

This module provides secure key storage using Windows Credential Manager
with DPAPI encryption for LazyScan's audit encryption system.
"""

import os
import sys
import time
import hashlib
import secrets
from typing import Optional

from . import KeyProvider, KeyNotFoundError, KeyProviderUnavailableError, KeyProviderPermissionError


# Check if we're on Windows
if os.name != "nt":
    # Not on Windows, provide a stub implementation
    class CredentialManagerKeyProvider(KeyProvider):
        def __init__(self, namespace: Optional[str] = None):
            raise KeyProviderUnavailableError("Credential Manager only available on Windows")

        def get_key(self, key_id: str) -> bytes:
            raise KeyProviderUnavailableError("Credential Manager only available on Windows")

        def store_key(self, key_id: str, key_data: bytes) -> None:
            raise KeyProviderUnavailableError("Credential Manager only available on Windows")

        def delete_key(self, key_id: str) -> bool:
            raise KeyProviderUnavailableError("Credential Manager only available on Windows")

        def key_exists(self, key_id: str) -> bool:
            raise KeyProviderUnavailableError("Credential Manager only available on Windows")

        def is_available(self) -> bool:
            return False

else:
    # Windows-specific implementation
    from ctypes import (
        Structure, c_void_p, c_wchar_p, c_char_p, c_ubyte,
        windll, POINTER, byref, cast
    )
    from ctypes.wintypes import DWORD

    # Windows API constants
    CRED_TYPE_GENERIC = 1
    CRED_PERSIST_LOCAL_MACHINE = 2

    # Error codes
    ERROR_NOT_FOUND = 1168
    ERROR_ACCESS_DENIED = 5

    # Credential flags
    CRED_FLAGS_DEFAULT = 0

    class CREDENTIAL_ATTRIBUTE(Structure):
        """Windows CREDENTIAL_ATTRIBUTE structure."""
        _fields_ = [
            ("Keyword", c_wchar_p),
            ("Flags", DWORD),
            ("ValueSize", DWORD),
            ("Value", c_void_p),
        ]

    class CREDENTIAL(Structure):
        """Windows CREDENTIAL structure."""
        _fields_ = [
            ("Flags", DWORD),
            ("Type", DWORD),
            ("TargetName", c_wchar_p),
            ("Comment", c_wchar_p),
            ("LastWritten", c_void_p),  # FILETIME
            ("CredentialBlobSize", DWORD),
            ("CredentialBlob", c_void_p),
            ("Persist", DWORD),
            ("AttributeCount", DWORD),
            ("Attributes", POINTER(CREDENTIAL_ATTRIBUTE)),
            ("TargetAlias", c_wchar_p),
            ("UserName", c_wchar_p),
        ]

    class CredentialManagerKeyProvider(KeyProvider):
        """
        Windows Credential Manager implementation of KeyProvider.

        Uses CredRead/CredWrite with CRED_TYPE_GENERIC to store AES-256 keys
        in the current user vault under a namespace unique to the installation.
        """

        def __init__(self, namespace: Optional[str] = None):
            """
            Initialize the Credential Manager key provider.

            Args:
                namespace: Unique namespace for this installation. If None,
                          generates one based on the executable path.
            """
            self.namespace = namespace or self._generate_namespace()

            # Check if we're running on Windows and can access the API
            if not self.is_available():
                raise KeyProviderUnavailableError("Windows Credential Manager API not available")

        def _generate_namespace(self) -> str:
            """Generate a unique namespace based on the installation path."""
            # Use the executable directory as a unique identifier
            exe_path = sys.executable
            exe_dir = os.path.dirname(exe_path)

            # Create a hash of the executable directory for uniqueness
            namespace_hash = hashlib.sha256(exe_dir.encode('utf-8')).hexdigest()[:16]
            return f"Lazyscan-{namespace_hash}"

        def _make_credential_name(self, key_id: str) -> str:
            """Create a unique credential name for the key."""
            return f"{self.namespace}-{key_id}"

        def _retry_operation(self, operation, max_retries: int = 3, delay: float = 0.1):
            """
            Retry an operation with exponential backoff for transient issues.

            Args:
                operation: Callable to retry
                max_retries: Maximum number of retries
                delay: Initial delay between retries

            Returns:
                Result of the operation

            Raises:
                The last exception if all retries fail
            """
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return operation()
                except (OSError, KeyProviderUnavailableError) as e:
                    last_exception = e
                    if attempt < max_retries:
                        time.sleep(delay * (2 ** attempt))  # Exponential backoff
                    else:
                        raise last_exception

        def get_key(self, key_id: str) -> bytes:
            """Retrieve a key from Windows Credential Manager."""
            def _read_credential():
                cred_name = self._make_credential_name(key_id)
                cred_ptr = POINTER(CREDENTIAL)()

                # Call CredReadW
                success = windll.advapi32.CredReadW(
                    cred_name,
                    CRED_TYPE_GENERIC,
                    0,
                    byref(cred_ptr)
                )

                if not success:
                    error_code = windll.kernel32.GetLastError()
                    if error_code == ERROR_NOT_FOUND:
                        raise KeyNotFoundError(f"Key '{key_id}' not found")
                    elif error_code == ERROR_ACCESS_DENIED:
                        raise KeyProviderPermissionError("Access denied to Credential Manager")
                    else:
                        raise KeyProviderUnavailableError(f"Credential Manager error: {error_code}")

                try:
                    cred = cred_ptr.contents
                    if cred.CredentialBlobSize == 0:
                        raise KeyNotFoundError(f"Key '{key_id}' is empty")

                    # Extract the credential blob (key data)
                    blob_size = cred.CredentialBlobSize
                    blob_ptr = cred.CredentialBlob

                    # Convert to bytes
                    key_data = bytes((c_ubyte * blob_size).from_address(blob_ptr))

                    return key_data

                finally:
                    # Free the credential
                    windll.advapi32.CredFree(cred_ptr)

            return self._retry_operation(_read_credential)

        def store_key(self, key_id: str, key_data: bytes) -> None:
            """Store a key in Windows Credential Manager."""
            def _write_credential():
                cred_name = self._make_credential_name(key_id)

                # Create credential structure
                cred = CREDENTIAL()
                cred.Flags = CRED_FLAGS_DEFAULT
                cred.Type = CRED_TYPE_GENERIC
                cred.TargetName = cred_name
                cred.Comment = f"Lazyscan audit encryption key: {key_id}"
                cred.CredentialBlobSize = len(key_data)

                # Allocate memory for the blob
                blob_array = (c_ubyte * len(key_data))(*key_data)
                cred.CredentialBlob = cast(blob_array, c_void_p)

                cred.Persist = CRED_PERSIST_LOCAL_MACHINE
                cred.AttributeCount = 0
                cred.Attributes = None
                cred.TargetAlias = None
                cred.UserName = None

                success = windll.advapi32.CredWriteW(byref(cred), 0)

                if not success:
                    error_code = windll.kernel32.GetLastError()
                    if error_code == ERROR_ACCESS_DENIED:
                        raise KeyProviderPermissionError("Access denied to Credential Manager")
                    else:
                        raise KeyProviderUnavailableError(f"Failed to store key: {error_code}")

            self._retry_operation(_write_credential)

        def delete_key(self, key_id: str) -> bool:
            """Delete a key from Windows Credential Manager."""
            def _delete_credential():
                cred_name = self._make_credential_name(key_id)

                success = windll.advapi32.CredDeleteW(cred_name, CRED_TYPE_GENERIC, 0)

                if not success:
                    error_code = windll.kernel32.GetLastError()
                    if error_code == ERROR_NOT_FOUND:
                        return False  # Key didn't exist
                    elif error_code == ERROR_ACCESS_DENIED:
                        raise KeyProviderPermissionError("Access denied to Credential Manager")
                    else:
                        raise KeyProviderUnavailableError(f"Failed to delete key: {error_code}")

                return True

            return self._retry_operation(_delete_credential)

        def key_exists(self, key_id: str) -> bool:
            """Check if a key exists in Windows Credential Manager."""
            try:
                self.get_key(key_id)
                return True
            except KeyNotFoundError:
                return False

        def is_available(self) -> bool:
            """Check if Windows Credential Manager is available."""
            try:
                # Try to access advapi32.dll functions
                return hasattr(windll.advapi32, 'CredReadW') and \
                       hasattr(windll.advapi32, 'CredWriteW') and \
                       hasattr(windll.advapi32, 'CredDeleteW')
            except:
                return False

        def generate_key(self, key_id: str, key_size: int = 32) -> bytes:
            """
            Generate a new random key and store it.

            Args:
                key_id: Unique identifier for the key
                key_size: Size of the key in bytes (default 32 for AES-256)

            Returns:
                The generated key data
            """
            key_data = secrets.token_bytes(key_size)
            self.store_key(key_id, key_data)
            return key_data

        def get_or_create_key(self, key_id: str, key_size: int = 32) -> bytes:
            """
            Get an existing key or create a new one if it doesn't exist.

            Args:
                key_id: Unique identifier for the key
                key_size: Size of the key in bytes (default 32 for AES-256)

            Returns:
                The key data
            """
            try:
                return self.get_key(key_id)
            except KeyNotFoundError:
                return self.generate_key(key_id, key_size)</content>
