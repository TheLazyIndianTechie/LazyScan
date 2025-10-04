#!/usr/bin/env python3
"""
Tests for Linux Secret Service Key Provider
"""

import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock

from lazyscan.security.key_providers import (
    SecretServiceKeyProvider,
    KeyNotFoundError,
    KeyProviderUnavailableError,
    KeyProviderPermissionError,
)


class TestSecretServiceKeyProvider:
    """Test the Linux Secret Service key provider."""

    @pytest.fixture
    def provider(self):
        """Create a test provider instance."""
        if not sys.platform.startswith("linux"):
            pytest.skip("Secret Service tests only run on Linux")
        return SecretServiceKeyProvider(namespace="test-namespace")

    def test_provider_creation_non_linux(self):
        """Test that the provider raises error on non-Linux systems."""
        if sys.platform.startswith("linux"):
            pytest.skip("This test is for non-Linux systems")

        with pytest.raises(KeyProviderUnavailableError, match="Secret Service only available on Linux"):
            SecretServiceKeyProvider()

    @patch('lazyscan.security.key_providers.secret_service_key_provider.SECRETSTORAGE_AVAILABLE', False)
    def test_provider_creation_no_secretstorage(self, monkeypatch):
        """Test that the provider raises error when secretstorage is not available."""
        if not sys.platform.startswith("linux"):
            pytest.skip("This test is for Linux systems")

        with pytest.raises(KeyProviderUnavailableError, match="secretstorage library not available"):
            SecretServiceKeyProvider()

    def test_namespace_generation(self):
        """Test that namespace is generated correctly."""
        if not sys.platform.startswith("linux"):
            pytest.skip("Linux only test")

        with patch('lazyscan.security.key_providers.secret_service_key_provider.SECRETSTORAGE_AVAILABLE', True):
            provider = SecretServiceKeyProvider()
            assert provider.namespace.startswith("Lazyscan-")
            assert len(provider.namespace) == 25  # "Lazyscan-" + 16 hex chars

    def test_make_item_label(self):
        """Test that item labels are generated correctly."""
        if not sys.platform.startswith("linux"):
            pytest.skip("Linux only test")

        with patch('lazyscan.security.key_providers.secret_service_key_provider.SECRETSTORAGE_AVAILABLE', True):
            provider = SecretServiceKeyProvider(namespace="test-ns")
            label = provider._make_item_label("test-key")
            assert label == "test-ns-test-key"

    def test_make_item_attributes(self):
        """Test that item attributes are generated correctly."""
        if not sys.platform.startswith("linux"):
            pytest.skip("Linux only test")

        with patch('lazyscan.security.key_providers.secret_service_key_provider.SECRETSTORAGE_AVAILABLE', True):
            provider = SecretServiceKeyProvider(namespace="test-ns")
            attrs = provider._make_item_attributes("test-key")
            expected = {
                "application": "lazyscan",
                "namespace": "test-ns",
                "key_id": "test-key",
                "type": "audit-encryption-key"
            }
            assert attrs == expected

    @patch('lazyscan.security.key_providers.secret_service_key_provider.secretstorage')
    def test_is_available_with_secretstorage(self, mock_secretstorage):
        """Test availability check when secretstorage is available."""
        if not sys.platform.startswith("linux"):
            pytest.skip("Linux only test")

        # Mock the availability check
        mock_secretstorage.check_service_availability.return_value = True

        with patch('lazyscan.security.key_providers.secret_service_key_provider.SECRETSTORAGE_AVAILABLE', True):
            provider = SecretServiceKeyProvider(namespace="test")
            assert provider.is_available()

            mock_secretstorage.check_service_availability.assert_called_once()

    @patch('lazyscan.security.key_providers.secret_service_key_provider.secretstorage')
    def test_is_available_service_unavailable(self, mock_secretstorage):
        """Test availability check when service is not available."""
        if not sys.platform.startswith("linux"):
            pytest.skip("Linux only test")

        # Mock service unavailable
        mock_secretstorage.check_service_availability.return_value = False

        with patch('lazyscan.security.key_providers.secret_service_key_provider.SECRETSTORAGE_AVAILABLE', True):
            provider = SecretServiceKeyProvider(namespace="test")
            assert not provider.is_available()

    @patch('lazyscan.security.key_providers.secret_service_key_provider.secretstorage')
    def test_store_and_retrieve_key(self, mock_secretstorage):
        """Test storing and retrieving a key."""
        if not sys.platform.startswith("linux"):
            pytest.skip("Linux only test")

        # Mock the secretstorage components
        mock_connection = Mock()
        mock_collection = Mock()
        mock_item = Mock()

        mock_secretstorage.dbus_init.return_value = mock_connection
        mock_secretstorage.get_collection_by_alias.return_value = mock_collection
        mock_collection.search_items.return_value = [mock_item]
        mock_item.get_secret.return_value = b"test-key-data"

        with patch('lazyscan.security.key_providers.secret_service_key_provider.SECRETSTORAGE_AVAILABLE', True):
            provider = SecretServiceKeyProvider(namespace="test")

            # Test storing a key
            test_key = b"12345678901234567890123456789012"  # 32 bytes
            provider.store_key("test-key", test_key)

            # Verify create_item was called
            mock_collection.create_item.assert_called_once()

            # Test retrieving a key
            retrieved_key = provider.get_key("test-key")

            # Verify search_items and get_secret were called
            mock_collection.search_items.assert_called()
            mock_item.get_secret.assert_called_once()
            assert retrieved_key == test_key

    @patch('lazyscan.security.key_providers.secret_service_key_provider.secretstorage')
    def test_key_not_found(self, mock_secretstorage):
        """Test handling of non-existent keys."""
        if not sys.platform.startswith("linux"):
            pytest.skip("Linux only test")

        # Mock the secretstorage components
        mock_connection = Mock()
        mock_collection = Mock()

        mock_secretstorage.dbus_init.return_value = mock_connection
        mock_secretstorage.get_collection_by_alias.return_value = mock_collection
        mock_collection.search_items.return_value = []  # No items found

        with patch('lazyscan.security.key_providers.secret_service_key_provider.SECRETSTORAGE_AVAILABLE', True):
            provider = SecretServiceKeyProvider(namespace="test")

            with pytest.raises(KeyNotFoundError):
                provider.get_key("non-existent-key")

    @patch('lazyscan.security.key_providers.secret_service_key_provider.secretstorage')
    def test_delete_key(self, mock_secretstorage):
        """Test deleting a key."""
        if not sys.platform.startswith("linux"):
            pytest.skip("Linux only test")

        # Mock the secretstorage components
        mock_connection = Mock()
        mock_collection = Mock()
        mock_item = Mock()

        mock_secretstorage.dbus_init.return_value = mock_connection
        mock_secretstorage.get_collection_by_alias.return_value = mock_collection
        mock_collection.search_items.return_value = [mock_item]

        with patch('lazyscan.security.key_providers.secret_service_key_provider.SECRETSTORAGE_AVAILABLE', True):
            provider = SecretServiceKeyProvider(namespace="test")

            # Test deleting existing key
            result = provider.delete_key("test-key")
            assert result is True
            mock_item.delete.assert_called_once()

            # Test deleting non-existent key
            mock_collection.search_items.return_value = []
            result = provider.delete_key("non-existent-key")
            assert result is False

    def test_key_exists(self):
        """Test key existence checking."""
        if not sys.platform.startswith("linux"):
            pytest.skip("Linux only test")

        with patch('lazyscan.security.key_providers.secret_service_key_provider.SECRETSTORAGE_AVAILABLE', True):
            provider = SecretServiceKeyProvider(namespace="test")

            # Test with a key that doesn't exist
            assert not provider.key_exists("non-existent-key")

    @patch('lazyscan.security.key_providers.secret_service_key_provider.secretstorage')
    def test_generate_key(self, mock_secretstorage):
        """Test key generation."""
        if not sys.platform.startswith("linux"):
            pytest.skip("Linux only test")

        # Mock the secretstorage components
        mock_connection = Mock()
        mock_collection = Mock()

        mock_secretstorage.dbus_init.return_value = mock_connection
        mock_secretstorage.get_collection_by_alias.return_value = mock_collection

        with patch('lazyscan.security.key_providers.secret_service_key_provider.SECRETSTORAGE_AVAILABLE', True):
            provider = SecretServiceKeyProvider(namespace="test")

            # Generate a key
            key_data = provider.generate_key("test-generated-key", key_size=32)

            # Verify the key was stored and returned
            assert len(key_data) == 32
            assert provider.key_exists("test-generated-key")

            # Verify create_item was called
            mock_collection.create_item.assert_called_once()

    @patch('lazyscan.security.key_providers.secret_service_key_provider.secretstorage')
    def test_get_or_create_key(self, mock_secretstorage):
        """Test get-or-create key functionality."""
        if not sys.platform.startswith("linux"):
            pytest.skip("Linux only test")

        # Mock the secretstorage components
        mock_connection = Mock()
        mock_collection = Mock()
        mock_item = Mock()

        mock_secretstorage.dbus_init.return_value = mock_connection
        mock_secretstorage.get_collection_by_alias.return_value = mock_collection

        with patch('lazyscan.security.key_providers.secret_service_key_provider.SECRETSTORAGE_AVAILABLE', True):
            provider = SecretServiceKeyProvider(namespace="test")

            # First call should create a new key
            key_data = provider.get_or_create_key("test-goc-key", key_size=32)
            assert len(key_data) == 32

            # Mock that the key now exists
            mock_collection.search_items.return_value = [mock_item]
            mock_item.get_secret.return_value = key_data

            # Second call should return the same key
            same_key_data = provider.get_or_create_key("test-goc-key", key_size=32)
            assert same_key_data == key_data

    @patch('lazyscan.security.key_providers.secret_service_key_provider.secretstorage')
    @patch('lazyscan.security.key_providers.secret_service_key_provider.time')
    def test_retry_logic_locked_exception(self, mock_time, mock_secretstorage):
        """Test retry logic for locked exceptions."""
        if not sys.platform.startswith("linux"):
            pytest.skip("Linux only test")

        from secretstorage.exceptions import LockedException

        # Mock the secretstorage components
        mock_connection = Mock()
        mock_collection = Mock()

        mock_secretstorage.dbus_init.return_value = mock_connection
        mock_secretstorage.get_collection_by_alias.return_value = mock_collection

        with patch('lazyscan.security.key_providers.secret_service_key_provider.SECRETSTORAGE_AVAILABLE', True):
            provider = SecretServiceKeyProvider(namespace="test")

            call_count = 0

            def failing_operation():
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise LockedException("Collection is locked")
                return "success"

            # Mock the queue operation to work
            with patch.object(provider, '_queue_operation') as mock_queue:
                mock_queue.return_value = "success"

                result = provider._retry_operation(failing_operation, max_retries=1)

                assert result == "success"
                assert call_count == 1  # Should have been called once, then queued
                mock_queue.assert_called_once()

    @patch('lazyscan.security.key_providers.secret_service_key_provider.secretstorage')
    @patch('lazyscan.security.key_providers.secret_service_key_provider.time')
    def test_retry_logic_service_unavailable(self, mock_time, mock_secretstorage):
        """Test retry logic for service unavailable exceptions."""
        if not sys.platform.startswith("linux"):
            pytest.skip("Linux only test")

        from secretstorage.exceptions import SecretServiceNotAvailableException

        # Mock the secretstorage components
        mock_connection = Mock()
        mock_collection = Mock()

        mock_secretstorage.dbus_init.return_value = mock_connection
        mock_secretstorage.get_collection_by_alias.return_value = mock_collection

        with patch('lazyscan.security.key_providers.secret_service_key_provider.SECRETSTORAGE_AVAILABLE', True):
            provider = SecretServiceKeyProvider(namespace="test")

            call_count = 0

            def failing_operation():
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise SecretServiceNotAvailableException("Service not available")
                return "success"

            result = provider._retry_operation(failing_operation, max_retries=3)

            assert result == "success"
            assert call_count == 3  # Should have been called 3 times
            assert mock_time.sleep.called  # Should have slept between retries

    @patch('lazyscan.security.key_providers.secret_service_key_provider.secretstorage')
    def test_collection_creation(self, mock_secretstorage):
        """Test that collection is created when it doesn't exist."""
        if not sys.platform.startswith("linux"):
            pytest.skip("Linux only test")

        from secretstorage.exceptions import ItemNotFoundException

        # Mock the secretstorage components
        mock_connection = Mock()
        mock_collection = Mock()

        mock_secretstorage.dbus_init.return_value = mock_connection
        mock_secretstorage.get_collection_by_alias.side_effect = ItemNotFoundException("Collection not found")
        mock_secretstorage.create_collection.return_value = mock_collection

        with patch('lazyscan.security.key_providers.secret_service_key_provider.SECRETSTORAGE_AVAILABLE', True):
            provider = SecretServiceKeyProvider(namespace="test")

            # Accessing collection should create it
            collection = provider._get_collection()

            assert collection == mock_collection
            mock_secretstorage.create_collection.assert_called_once_with(
                mock_connection, "LazyScan", "LazyScan audit encryption keys"
            )

    @patch('lazyscan.security.key_providers.secret_service_key_provider.secretstorage')
    def test_worker_thread_cleanup(self, mock_secretstorage):
        """Test that worker thread is properly cleaned up."""
        if not sys.platform.startswith("linux"):
            pytest.skip("Linux only test")

        # Mock the secretstorage components
        mock_connection = Mock()
        mock_collection = Mock()

        mock_secretstorage.dbus_init.return_value = mock_connection
        mock_secretstorage.get_collection_by_alias.return_value = mock_collection

        with patch('lazyscan.security.key_providers.secret_service_key_provider.SECRETSTORAGE_AVAILABLE', True):
            provider = SecretServiceKeyProvider(namespace="test")

            # Verify worker thread was started
            assert provider._worker_thread is not None
            assert provider._worker_thread.is_alive()

            # Cleanup
            del provider

            # Note: Thread cleanup is tested implicitly through the __del__ method