#!/usr/bin/env python3
"""
Linux Secret Service Key Provider

This module provides secure key storage using the FreeDesktop.org Secret Service
API (D-Bus) with libsecret fallback for LazyScan's audit encryption system.
"""

import os
import sys
import time
import hashlib
import secrets
import threading
from typing import Optional, List, Any, Dict
from queue import Queue, Empty
import logging

from . import KeyProvider, KeyNotFoundError, KeyProviderUnavailableError, KeyProviderPermissionError

# Check if we're on Linux
if not sys.platform.startswith("linux"):
    # Not on Linux, provide a stub implementation
    class SecretServiceKeyProvider(KeyProvider):
        def __init__(self, namespace: Optional[str] = None):
            raise KeyProviderUnavailableError("Secret Service only available on Linux")

        def get_key(self, key_id: str) -> bytes:
            raise KeyProviderUnavailableError("Secret Service only available on Linux")

        def store_key(self, key_id: str, key_data: bytes) -> None:
            raise KeyProviderUnavailableError("Secret Service only available on Linux")

        def delete_key(self, key_id: str) -> bool:
            raise KeyProviderUnavailableError("Secret Service only available on Linux")

        def key_exists(self, key_id: str) -> bool:
            raise KeyProviderUnavailableError("Secret Service only available on Linux")

        def is_available(self) -> bool:
            return False

else:
    # Linux-specific implementation
    try:
        import secretstorage
        from secretstorage.exceptions import (
            ItemNotFoundException,
            LockedException,
            PromptDismissedException,
            SecretServiceNotAvailableException,
            SecretStorageException,
        )
        SECRETSTORAGE_AVAILABLE = True
    except ImportError:
        SECRETSTORAGE_AVAILABLE = False

    class SecretServiceKeyProvider(KeyProvider):
        """
        Linux Secret Service implementation of KeyProvider.

        Uses the FreeDesktop.org Secret Service API (D-Bus) to store AES-256 keys
        in a collection with attributes for secure lookup. Handles locked sessions
        with queuing and retry logic for headless environments.
        """

        def __init__(self, namespace: Optional[str] = None, collection_name: str = "LazyScan"):
            """
            Initialize the Secret Service key provider.

            Args:
                namespace: Unique namespace for this installation. If None,
                          generates one based on the executable path.
                collection_name: Name of the secret service collection to use.
            """
            if not SECRETSTORAGE_AVAILABLE:
                raise KeyProviderUnavailableError("secretstorage library not available")

            self.namespace = namespace or self._generate_namespace()
            self.collection_name = collection_name
            self._connection = None
            self._collection = None
            self._lock = threading.RLock()
            self._pending_operations = Queue()
            self._worker_thread = None
            self._shutdown_event = threading.Event()

            # Check if we're running on Linux and can access the Secret Service
            if not self.is_available():
                raise KeyProviderUnavailableError("Secret Service not available")

            # Start background worker for handling locked sessions
            self._start_worker_thread()

        def _generate_namespace(self) -> str:
            """Generate a unique namespace based on the installation path."""
            # Use the executable directory as a unique identifier
            exe_path = sys.executable
            exe_dir = os.path.dirname(exe_path)

            # Create a hash of the executable directory for uniqueness
            namespace_hash = hashlib.sha256(exe_dir.encode('utf-8')).hexdigest()[:16]
            return f"Lazyscan-{namespace_hash}"

        def _get_connection(self):
            """Get or create D-Bus connection."""
            if self._connection is None:
                try:
                    self._connection = secretstorage.dbus_init()
                except Exception as e:
                    raise KeyProviderUnavailableError(f"Failed to initialize D-Bus: {e}")
            return self._connection

        def _get_collection(self):
            """Get or create the secret service collection."""
            if self._collection is None:
                try:
                    connection = self._get_connection()
                    # Try to get existing collection first
                    try:
                        self._collection = secretstorage.get_collection_by_alias(
                            connection, self.collection_name
                        )
                    except ItemNotFoundException:
                        # Collection doesn't exist, create it
                        self._collection = secretstorage.create_collection(
                            connection, self.collection_name, "LazyScan audit encryption keys"
                        )
                except SecretServiceNotAvailableException:
                    raise KeyProviderUnavailableError("Secret Service daemon not available")
                except Exception as e:
                    raise KeyProviderUnavailableError(f"Failed to access collection: {e}")
            return self._collection

        def _make_item_label(self, key_id: str) -> str:
            """Create a unique item label for the key."""
            return f"{self.namespace}-{key_id}"

        def _make_item_attributes(self, key_id: str) -> Dict[str, str]:
            """Create lookup attributes for the key item."""
            return {
                "application": "lazyscan",
                "namespace": self.namespace,
                "key_id": key_id,
                "type": "audit-encryption-key"
            }

        def _start_worker_thread(self):
            """Start background worker thread for handling queued operations."""
            if self._worker_thread is None or not self._worker_thread.is_alive():
                self._worker_thread = threading.Thread(
                    target=self._worker_loop,
                    daemon=True,
                    name="SecretServiceWorker"
                )
                self._worker_thread.start()

        def _worker_loop(self):
            """Background worker loop for processing queued operations."""
            while not self._shutdown_event.is_set():
                try:
                    # Wait for an operation with timeout
                    operation = self._pending_operations.get(timeout=1.0)
                    if operation:
                        operation()
                except Empty:
                    continue
                except Exception as e:
                    logging.warning(f"Secret Service worker error: {e}")

        def _queue_operation(self, operation, timeout: float = 30.0):
            """
            Queue an operation for execution, handling locked sessions.

            Args:
                operation: Callable to execute
                timeout: Maximum time to wait for operation completion

            Returns:
                Result of the operation

            Raises:
                TimeoutError: If operation times out
            """
            result_queue = Queue()

            def wrapped_operation():
                try:
                    result = operation()
                    result_queue.put(("success", result))
                except Exception as e:
                    result_queue.put(("error", e))

            # Queue the operation
            self._pending_operations.put(wrapped_operation)

            # Wait for result
            try:
                status, value = result_queue.get(timeout=timeout)
                if status == "error":
                    raise value
                return value
            except Empty:
                raise TimeoutError(f"Operation timed out after {timeout} seconds")

        def _retry_operation(self, operation, max_retries: int = 3, delay: float = 0.5):
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
                except (LockedException, SecretServiceNotAvailableException) as e:
                    last_exception = e
                    if attempt < max_retries:
                        # For locked exceptions, queue the operation
                        if isinstance(e, LockedException):
                            return self._queue_operation(operation)
                        # For service unavailable, wait and retry
                        time.sleep(delay * (2 ** attempt))
                    else:
                        raise last_exception
                except (OSError, SecretStorageException) as e:
                    last_exception = e
                    if attempt < max_retries:
                        time.sleep(delay * (2 ** attempt))
                    else:
                        raise last_exception

        def _find_item(self, key_id: str):
            """Find an item by key_id."""
            collection = self._get_collection()
            attributes = self._make_item_attributes(key_id)
            items = collection.search_items(attributes)

            # Return the first matching item
            for item in items:
                return item

            raise ItemNotFoundException(f"Key '{key_id}' not found")

        def get_key(self, key_id: str) -> bytes:
            """Retrieve a key from Secret Service."""
            def _read_item():
                try:
                    item = self._find_item(key_id)
                    secret = item.get_secret()
                    if not secret:
                        raise KeyNotFoundError(f"Key '{key_id}' is empty")
                    return secret
                except ItemNotFoundException:
                    raise KeyNotFoundError(f"Key '{key_id}' not found")

            with self._lock:
                return self._retry_operation(_read_item)

        def store_key(self, key_id: str, key_data: bytes) -> None:
            """Store a key in Secret Service."""
            def _write_item():
                collection = self._get_collection()
                label = self._make_item_label(key_id)
                attributes = self._make_item_attributes(key_id)

                # Check if item already exists
                try:
                    existing_item = self._find_item(key_id)
                    # Update existing item
                    existing_item.set_secret(key_data)
                except ItemNotFoundException:
                    # Create new item
                    collection.create_item(label, attributes, key_data)

            with self._lock:
                self._retry_operation(_write_item)

        def delete_key(self, key_id: str) -> bool:
            """Delete a key from Secret Service."""
            def _delete_item():
                try:
                    item = self._find_item(key_id)
                    item.delete()
                    return True
                except ItemNotFoundException:
                    return False  # Key didn't exist

            with self._lock:
                return self._retry_operation(_delete_item)

        def key_exists(self, key_id: str) -> bool:
            """Check if a key exists in Secret Service."""
            try:
                self.get_key(key_id)
                return True
            except KeyNotFoundError:
                return False

        def is_available(self) -> bool:
            """Check if Secret Service is available."""
            if not SECRETSTORAGE_AVAILABLE:
                return False

            try:
                # Check if secret service is available
                connection = self._get_connection()
                return secretstorage.check_service_availability(connection)
            except Exception:
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
                return self.generate_key(key_id, key_size)

        def __del__(self):
            """Cleanup resources."""
            self._shutdown_event.set()
            if self._worker_thread and self._worker_thread.is_alive():
                self._worker_thread.join(timeout=5.0)
            if self._connection:
                try:
                    self._connection.close()
                except Exception:
                    pass