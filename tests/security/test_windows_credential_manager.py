#!/usr/bin/env python3
"""
Tests for Windows Credential Manager Key Provider
"""

import os
import pytest
from unittest.mock import Mock, patch

from lazyscan.security.key_providers import (
    CredentialManagerKeyProvider,
    KeyNotFoundError,
    KeyProviderUnavailableError,
    KeyProviderPermissionError,
)


class TestCredentialManagerKeyProvider:
    """Test the Windows Credential Manager key provider."""

    @pytest.fixture
    def provider(self):
        """Create a test provider instance."""
        if os.name != "nt":
            pytest.skip("Windows Credential Manager tests only run on Windows")
        return CredentialManagerKeyProvider(namespace="test-namespace")

    def test_provider_creation(self):
        """Test that the provider can be created on Windows."""
        if os.name != "nt":
            with pytest.raises(KeyProviderUnavailableError):
                CredentialManagerKeyProvider()
        else:
            provider = CredentialManagerKeyProvider(namespace="test")
            assert provider.namespace == "test"
            assert provider.is_available()

    def test_namespace_generation(self):
        """Test that namespace is generated correctly."""
        if os.name != "nt":
            pytest.skip("Windows only test")

        provider = CredentialManagerKeyProvider()
        assert provider.namespace.startswith("Lazyscan-")
        assert len(provider.namespace) == 25  # "Lazyscan-" + 16 hex chars

    def test_credential_name_generation(self):
        """Test that credential names are generated correctly."""
        if os.name != "nt":
            pytest.skip("Windows only test")

        provider = CredentialManagerKeyProvider(namespace="test-ns")
        name = provider._make_credential_name("test-key")
        assert name == "test-ns-test-key"

    def test_is_available_on_windows(self):
        """Test availability check on Windows."""
        if os.name == "nt":
            provider = CredentialManagerKeyProvider(namespace="test")
            assert provider.is_available()
        else:
            # On non-Windows systems, should not be available
            assert not CredentialManagerKeyProvider.is_available(None)

    def test_is_available_on_non_windows(self):
        """Test availability check on non-Windows systems."""
        if os.name != "nt":
            assert not CredentialManagerKeyProvider.is_available(None)

    @patch('lazyscan.security.key_providers.windows_credential_manager.windll')
    def test_store_and_retrieve_key(self, mock_windll):
        """Test storing and retrieving a key."""
        if os.name != "nt":
            pytest.skip("Windows only test")

        # Mock the Windows API calls
        mock_advapi32 = Mock()
        mock_kernel32 = Mock()
        mock_windll.advapi32 = mock_advapi32
        mock_windll.kernel32 = mock_kernel32

        # Mock successful operations
        mock_advapi32.CredWriteW.return_value = 1  # Success
        mock_advapi32.CredReadW.return_value = 1   # Success
        mock_advapi32.CredFree.return_value = None

        # Mock credential structure
        mock_cred = Mock()
        mock_cred.contents.CredentialBlobSize = 32
        mock_cred.contents.CredentialBlob = Mock()

        # Mock the credential blob data
        test_key = b"12345678901234567890123456789012"  # 32 bytes
        mock_cred.contents.CredentialBlob.__class__ = type('MockBlob', (), {
            'from_address': Mock(return_value=test_key)
        })()

        with patch('lazyscan.security.key_providers.windows_credential_manager.POINTER') as mock_pointer:
            mock_pointer.return_value = mock_cred

            provider = CredentialManagerKeyProvider(namespace="test")

            # Test storing a key
            provider.store_key("test-key", test_key)

            # Verify CredWriteW was called
            assert mock_advapi32.CredWriteW.called

            # Test retrieving a key
            retrieved_key = provider.get_key("test-key")

            # Verify CredReadW was called
            assert mock_advapi32.CredReadW.called
            assert retrieved_key == test_key

    @patch('lazyscan.security.key_providers.windows_credential_manager.windll')
    def test_key_not_found(self, mock_windll):
        """Test handling of non-existent keys."""
        if os.name != "nt":
            pytest.skip("Windows only test")

        # Mock the Windows API calls
        mock_advapi32 = Mock()
        mock_kernel32 = Mock()
        mock_windll.advapi32 = mock_advapi32
        mock_windll.kernel32 = mock_kernel32

        # Mock CredReadW to fail with ERROR_NOT_FOUND
        mock_advapi32.CredReadW.return_value = 0  # Failure
        mock_kernel32.GetLastError.return_value = 1168  # ERROR_NOT_FOUND

        provider = CredentialManagerKeyProvider(namespace="test")

        with pytest.raises(KeyNotFoundError):
            provider.get_key("non-existent-key")

    @patch('lazyscan.security.key_providers.windows_credential_manager.windll')
    def test_access_denied(self, mock_windll):
        """Test handling of access denied errors."""
        if os.name != "nt":
            pytest.skip("Windows only test")

        # Mock the Windows API calls
        mock_advapi32 = Mock()
        mock_kernel32 = Mock()
        mock_windll.advapi32 = mock_advapi32
        mock_windll.kernel32 = mock_kernel32

        # Mock CredReadW to fail with ERROR_ACCESS_DENIED
        mock_advapi32.CredReadW.return_value = 0  # Failure
        mock_kernel32.GetLastError.return_value = 5  # ERROR_ACCESS_DENIED

        provider = CredentialManagerKeyProvider(namespace="test")

        with pytest.raises(KeyProviderPermissionError):
            provider.get_key("test-key")

    def test_key_exists(self):
        """Test key existence checking."""
        if os.name != "nt":
            pytest.skip("Windows only test")

        provider = CredentialManagerKeyProvider(namespace="test")

        # Test with a key that doesn't exist
        assert not provider.key_exists("non-existent-key")

    def test_generate_key(self):
        """Test key generation."""
        if os.name != "nt":
            pytest.skip("Windows only test")

        provider = CredentialManagerKeyProvider(namespace="test")

        # Generate a key
        key_data = provider.generate_key("test-generated-key", key_size=32)

        # Verify the key was stored and returned
        assert len(key_data) == 32
        assert provider.key_exists("test-generated-key")

        # Verify we can retrieve it
        retrieved_key = provider.get_key("test-generated-key")
        assert retrieved_key == key_data

    def test_get_or_create_key(self):
        """Test get-or-create key functionality."""
        if os.name != "nt":
            pytest.skip("Windows only test")

        provider = CredentialManagerKeyProvider(namespace="test")

        # Create a new key
        key_data = provider.get_or_create_key("test-goc-key", key_size=32)
        assert len(key_data) == 32

        # Get the same key again
        same_key_data = provider.get_or_create_key("test-goc-key", key_size=32)
        assert same_key_data == key_data

    @patch('lazyscan.security.key_providers.windows_credential_manager.time')
    def test_retry_logic(self, mock_time):
        """Test retry logic for transient failures."""
        if os.name != "nt":
            pytest.skip("Windows only test")

        provider = CredentialManagerKeyProvider(namespace="test")

        call_count = 0

        def failing_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise OSError("Transient error")
            return "success"

        result = provider._retry_operation(failing_operation, max_retries=3)

        assert result == "success"
        assert call_count == 3  # Should have been called 3 times
        assert mock_time.sleep.called  # Should have slept between retries