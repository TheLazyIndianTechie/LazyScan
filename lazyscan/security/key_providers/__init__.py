#!/usr/bin/env python3
"""
Key Provider Abstraction for Secure Key Management

This module provides a cross-platform abstraction for secure key storage
and retrieval using platform-native secure storage mechanisms.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple
from enum import Enum
import os
import sys

from ..audit_encryption_schema import KeyProvider as KeyProviderEnum


class KeyProviderError(Exception):
    """Base exception for key provider operations."""
    pass


class KeyNotFoundError(KeyProviderError):
    """Raised when a requested key is not found."""
    pass


class KeyProviderUnavailableError(KeyProviderError):
    """Raised when the key provider is not available."""
    pass


class KeyProviderPermissionError(KeyProviderError):
    """Raised when access to the key provider is denied."""
    pass


class KeyProvider(ABC):
    """
    Abstract base class for key providers.

    Key providers handle secure storage and retrieval of cryptographic keys
    using platform-native secure storage mechanisms.
    """

    @abstractmethod
    def get_key(self, key_id: str) -> bytes:
        """
        Retrieve a key by ID.

        Args:
            key_id: Unique identifier for the key

        Returns:
            The key data as bytes

        Raises:
            KeyNotFoundError: If the key doesn't exist
            KeyProviderUnavailableError: If the provider is unavailable
            KeyProviderPermissionError: If access is denied
        """
        pass

    @abstractmethod
    def store_key(self, key_id: str, key_data: bytes) -> None:
        """
        Store a key with the given ID.

        Args:
            key_id: Unique identifier for the key
            key_data: The key data to store

        Raises:
            KeyProviderUnavailableError: If the provider is unavailable
            KeyProviderPermissionError: If access is denied
        """
        pass

    @abstractmethod
    def delete_key(self, key_id: str) -> bool:
        """
        Delete a key by ID.

        Args:
            key_id: Unique identifier for the key

        Returns:
            True if the key was deleted, False if it didn't exist

        Raises:
            KeyProviderUnavailableError: If the provider is unavailable
            KeyProviderPermissionError: If access is denied
        """
        pass

    @abstractmethod
    def key_exists(self, key_id: str) -> bool:
        """
        Check if a key exists.

        Args:
            key_id: Unique identifier for the key

        Returns:
            True if the key exists, False otherwise

        Raises:
            KeyProviderUnavailableError: If the provider is unavailable
            KeyProviderPermissionError: If access is denied
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the key provider is available on this system.

        Returns:
            True if the provider is available, False otherwise
        """
        pass


def get_key_provider(provider_type: str) -> KeyProvider:
    """
    Factory function to create the appropriate key provider for the platform.

    Args:
        provider_type: The type of key provider to create

    Returns:
        A KeyProvider instance

    Raises:
        ValueError: If the provider type is not supported
    """
    if provider_type == KeyProviderEnum.KEYCHAIN.value:
        if sys.platform == "darwin":
            # TODO: Implement macOS Keychain provider
            raise NotImplementedError("macOS Keychain provider not yet implemented")
        else:
            raise ValueError(f"Keychain provider not available on {sys.platform}")

    elif provider_type == KeyProviderEnum.CREDENTIAL_MANAGER.value:
        if os.name == "nt":
            from .windows_credential_manager import CredentialManagerKeyProvider
            return CredentialManagerKeyProvider()
        else:
            raise ValueError(f"Credential Manager provider not available on {sys.platform}")

    elif provider_type == KeyProviderEnum.SECRET_SERVICE.value:
        if sys.platform.startswith("linux"):
            from .secret_service_key_provider import SecretServiceKeyProvider
            return SecretServiceKeyProvider()
        else:
            raise ValueError(f"Secret Service provider not available on {sys.platform}")

    else:
        raise ValueError(f"Unsupported key provider: {provider_type}")


def get_platform_key_provider() -> KeyProvider:
    """
    Get the default key provider for the current platform.

    Returns:
        A KeyProvider instance appropriate for the current platform
    """
    if sys.platform == "darwin":
        return get_key_provider(KeyProviderEnum.KEYCHAIN.value)
    elif os.name == "nt":
        return get_key_provider(KeyProviderEnum.CREDENTIAL_MANAGER.value)
    else:  # Linux and others
        return get_key_provider(KeyProviderEnum.SECRET_SERVICE.value)


__all__ = [
    "KeyProvider",
    "KeyProviderError",
    "KeyNotFoundError",
    "KeyProviderUnavailableError",
    "KeyProviderPermissionError",
    "get_key_provider",
    "get_platform_key_provider",
]