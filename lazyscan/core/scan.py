#!/usr/bin/env python3
"""
Async directory scanning functionality for LazyScan.
Provides asyncio-based file system traversal with progress callbacks and concurrency control.
"""

import asyncio
import dataclasses
import os
import time
from pathlib import Path
from typing import Optional, Callable, List, Tuple, Dict, Any, Union, Awaitable, cast
from concurrent.futures import ThreadPoolExecutor

from ..core.logging_config import get_logger
from ..core.config import get_scanning_setting

logger = get_logger(__name__)


@dataclasses.dataclass
class ScanResult:
    """Structured result from async directory scanning."""
    total_size: int
    file_count: int
    dir_count: int
    files: List[Tuple[str, int]]
    errors: List[Tuple[str, str]]
    scan_duration: float
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary with stable JSON schema.

        Returns:
            Dictionary representation for JSON serialization
        """
        from .serialization import scan_result_to_dict
        return scan_result_to_dict(self)


class AsyncProgressEmitter:
    """Manages progress callbacks with batching to prevent UI flooding."""

    def __init__(self, callback: Optional[Callable] = None, batch_interval: float = 0.1):
        self.callback = callback
        self.batch_interval = batch_interval
        self.pending_updates: List[Tuple[Path, Any]] = []
        self.last_emit = 0.0
        self._task: Optional[asyncio.Task] = None
        self._shutdown = False

    async def emit(self, path: Path, data: Any) -> None:
        """Queue a progress update for batching."""
        if self.callback is None:
            return

        self.pending_updates.append((path, data))

        # Start batching task if not already running
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._batch_emit())

    async def _batch_emit(self) -> None:
        """Batch and emit progress updates at regular intervals."""
        try:
            while not self._shutdown and self.pending_updates:
                # Wait for batch interval
                await asyncio.sleep(self.batch_interval)

                # Emit all pending updates
                updates = self.pending_updates.copy()
                self.pending_updates.clear()

                for path, data in updates:
                    try:
                        if self.callback is not None:
                            # Handle both sync and async callbacks
                            if asyncio.iscoroutinefunction(self.callback):
                                await self.callback(path, data)  # type: ignore
                            else:
                                # Run sync callback in executor
                                def call_callback() -> None:
                                    self.callback(path, data)  # type: ignore
                                await asyncio.get_event_loop().run_in_executor(None, call_callback)  # type: ignore[arg-type]
                    except Exception as e:
                        logger.debug("Progress callback failed", path=str(path), error=str(e))

        except asyncio.CancelledError:
            # Emit any remaining updates on cancellation
            if self.pending_updates and not self._shutdown:
                for path, data in self.pending_updates:
                    try:
                        if asyncio.iscoroutinefunction(self.callback):
                            await self.callback(path, data)
                        else:
                            await asyncio.get_event_loop().run_in_executor(
                                None, self.callback, path, data  # type: ignore[arg-type]
                            )
                    except Exception as e:
                        logger.debug("Final progress callback failed", path=str(path), error=str(e))
            raise

    async def shutdown(self) -> None:
        """Shutdown the emitter and emit any remaining updates."""
        self._shutdown = True
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                # Emit any remaining updates after cancellation
                for path, data in self.pending_updates:
                    try:
                        if self.callback is not None:
                            # For now, assume sync callback and run in executor
                            def call_callback():
                                self.callback(path, data)  # type: ignore[arg-type]
                            loop = asyncio.get_event_loop()
                            await loop.run_in_executor(None, call_callback)
                    except Exception as e:
                        logger.debug("Shutdown progress callback failed", path=str(path), error=str(e))
                self.pending_updates.clear()


async def scan_directory(
    path: Path,
    *,
    max_depth: Optional[int] = None,
    exclude_patterns: Optional[List[str]] = None,
    min_size_bytes: int = 0,
    progress_callback: Optional[Callable[[Path, Any], Any]] = None,
    concurrency_limit: int = 10
) -> Dict[str, Any]:
    """Async directory scan implementation."""
    logger.debug(f"Starting async scan of {path}")
    """
    Asynchronously scan a directory tree and return aggregated file information.

    This function provides concurrent directory traversal using asyncio, with filesystem
    operations offloaded to thread executors to maintain performance while keeping
    the event loop responsive.

    Args:
        path: Root directory path to scan
        max_depth: Maximum directory depth to traverse (None for unlimited)
        exclude_patterns: List of glob patterns to exclude from scanning
        min_size_bytes: Minimum file size in bytes to include (default: 0)
        progress_callback: Optional callback for progress updates. Can be sync or async.
                          Called with (path, data) where data contains scan results.
        concurrency_limit: Maximum concurrent directory operations (default: from config)

    Returns:
        Dictionary containing:
        - 'total_size': Total bytes of all files
        - 'file_count': Total number of files
        - 'dir_count': Total number of directories
        - 'files': List of (path, size) tuples for all files
        - 'errors': List of (path, error) tuples for failed operations

    Raises:
        ValueError: If path is not a directory or doesn't exist
        asyncio.CancelledError: If the scan is cancelled
    """
    if not path.exists():
        raise ValueError(f"Path does not exist: {path}")

    if not path.is_dir():
        raise ValueError(f"Path is not a directory: {path}")

    # Get concurrency limit from config if not specified
    if concurrency_limit is None:
        concurrency_limit = get_scanning_setting("max_concurrency", 10)

    # Ensure concurrency_limit is an int
    concurrency_limit = int(concurrency_limit)

    logger.debug(f"Using concurrency limit: {concurrency_limit}")

    # Initialize progress emitter
    progress_emitter = AsyncProgressEmitter(progress_callback)

    try:
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(int(concurrency_limit))

        # Initialize result accumulator
        result = {
            'total_size': 0,
            'file_count': 0,
            'dir_count': 0,
            'files': [],
            'errors': []
        }

        # Start recursive scan
        await _scan_recursive(
            path,
            result,
            semaphore,
            progress_emitter,
            max_depth=max_depth,
            exclude_patterns=exclude_patterns,
            min_size_bytes=min_size_bytes,
            depth=0
        )

        # Emit final progress update
        await progress_emitter.emit(path, result)

        logger.info(
            "Async directory scan completed",
            path=str(path),
            files=result['file_count'],
            dirs=result['dir_count'],
            total_size=result['total_size']
        )

        return result

    finally:
        await progress_emitter.shutdown()


async def _scan_recursive(
    dir_path: Path,
    result: Dict[str, Any],
    semaphore: asyncio.Semaphore,
    progress_emitter: AsyncProgressEmitter,
    *,
    max_depth: Optional[int] = None,
    exclude_patterns: Optional[List[str]] = None,
    min_size_bytes: int = 0,
    depth: int = 0
) -> None:
    """
    Recursively scan a directory with concurrency control.

    Args:
        dir_path: Directory to scan
        result: Accumulator dictionary for results
        semaphore: Semaphore for concurrency control
        progress_emitter: Progress callback manager
        max_depth: Maximum depth to traverse
        exclude_patterns: Patterns to exclude
        min_size_bytes: Minimum file size to include
        depth: Current depth in tree
    """
    # Check depth limit
    if max_depth is not None and depth >= max_depth:
        return

    async with semaphore:
        try:
            # List directory contents (blocking I/O offloaded to thread)
            entries = await asyncio.to_thread(_list_dir_safe, dir_path)

            # Filter entries based on exclude patterns
            if exclude_patterns:
                filtered_entries = []
                for entry in entries:
                    if not _matches_exclude_patterns(entry, exclude_patterns):
                        filtered_entries.append(entry)
                entries = filtered_entries

            # Count this directory
            result['dir_count'] += 1

            # Process entries concurrently
            tasks = []
            for entry in entries:
                if entry.is_dir():
                    # Recurse into subdirectory
                    task = asyncio.create_task(_scan_recursive(
                        entry,
                        result,
                        semaphore,
                        progress_emitter,
                        max_depth=max_depth,
                        exclude_patterns=exclude_patterns,
                        min_size_bytes=min_size_bytes,
                        depth=depth + 1
                    ))
                    tasks.append(task)
                else:
                    # Process file
                    task = asyncio.create_task(_process_file(entry, result, min_size_bytes))
                    tasks.append(task)

            # Wait for all child operations to complete
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

            # Emit progress update for this directory
            dir_summary = {
                'path': str(dir_path),
                'depth': depth,
                'files_processed': len([e for e in entries if e.is_file()]),
                'subdirs': len([e for e in entries if e.is_dir()])
            }
            await progress_emitter.emit(dir_path, dir_summary)

        except Exception as e:
            logger.warning(
                "Failed to scan directory",
                path=str(dir_path),
                error=str(e)
            )
            result['errors'].append((str(dir_path), str(e)))


async def _process_file(file_path: Path, result: Dict[str, Any], min_size_bytes: int = 0) -> None:
    """Process a single file and update results."""
    try:
        # Get file size (blocking I/O offloaded to thread)
        size = await asyncio.to_thread(_get_file_size_safe, file_path)

        # Filter by minimum size
        if size < min_size_bytes:
            return

        # Update results
        result['file_count'] += 1
        result['total_size'] += size
        result['files'].append((str(file_path), size))

    except Exception as e:
        logger.debug(
            "Failed to process file",
            path=str(file_path),
            error=str(e)
        )
        result['errors'].append((str(file_path), str(e)))


def _list_dir_safe(dir_path: Path) -> List[Path]:
    """Safely list directory contents."""
    try:
        return list(dir_path.iterdir())
    except (OSError, PermissionError) as e:
        logger.debug("Failed to list directory", path=str(dir_path), error=str(e))
        return []


def _get_file_size_safe(file_path: Path) -> int:
    """Safely get file size."""
    try:
        return file_path.stat().st_size
    except (OSError, PermissionError) as e:
        logger.debug("Failed to get file size", path=str(file_path), error=str(e))
        return 0


def _matches_exclude_patterns(path: Path, patterns: List[str]) -> bool:
    """Check if path matches any exclude pattern."""
    import fnmatch

    path_str = str(path)
    name = path.name

    for pattern in patterns:
        # Check against full path and filename
        if fnmatch.fnmatch(path_str, pattern) or fnmatch.fnmatch(name, pattern):
            return True

    return False


# New asyncio-based producer-consumer scanning implementation
async def scan_directory_async(
    path: Path,
    *,
    follow_symlinks: bool = False,
    semaphore: Optional[asyncio.Semaphore] = None,
    progress_callback: Optional[Callable[[Path, Dict[str, Any]], Awaitable[None]]] = None,
    max_depth: Optional[int] = None,
    exclude_patterns: Optional[List[str]] = None,
    min_size_bytes: int = 0
) -> ScanResult:
    """
    Async directory scanning using producer-consumer pattern with structured results.

    This function implements the asyncio-based scanning engine upgrade, using a
    producer-consumer pattern with asyncio.Queue for efficient, non-blocking
    directory traversal and progress reporting.

    Args:
        path: Root directory path to scan
        follow_symlinks: Whether to follow symbolic links (default: False)
        semaphore: Optional external semaphore for concurrency control
        progress_callback: Optional async callback for progress updates
        max_depth: Maximum directory depth to traverse (None for unlimited)
        exclude_patterns: List of glob patterns to exclude from scanning
        min_size_bytes: Minimum file size in bytes to include (default: 0)

    Returns:
        ScanResult with structured scan data and metadata

    Raises:
        ValueError: If path is not a directory or doesn't exist
        asyncio.CancelledError: If the scan is cancelled
    """
    if not path.exists():
        raise ValueError(f"Path does not exist: {path}")

    if not path.is_dir():
        raise ValueError(f"Path is not a directory: {path}")

    start_time = time.time()
    logger.debug("Starting async producer-consumer scan", path=str(path))

    # Create result accumulator
    result = ScanResult(
        total_size=0,
        file_count=0,
        dir_count=0,
        files=[],
        errors=[],
        scan_duration=0.0,
        metadata={"path": str(path), "follow_symlinks": follow_symlinks}
    )

    # Create queue for producer-consumer communication
    queue: asyncio.Queue[Union[Path, Tuple[str, Union[str, int]], None]] = asyncio.Queue(maxsize=1000)

    # Use provided semaphore or create default based on CPU count
    if semaphore is None:
        concurrency_limit = min(32, (os.cpu_count() or 4) + 4)
        semaphore = asyncio.Semaphore(concurrency_limit)

    try:
        async with asyncio.TaskGroup() as tg:
            # Start producer task
            tg.create_task(_walk_tree_async(
                path, queue, semaphore, follow_symlinks,
                max_depth=max_depth,
                exclude_patterns=exclude_patterns,
                min_size_bytes=min_size_bytes
            ))

            # Start consumer task
            tg.create_task(_aggregate_results_async(queue, result, progress_callback))

    except Exception as e:
        logger.error("Async scan failed", path=str(path), error=str(e))
        result.errors.append((str(path), str(e)))
        raise

    # Calculate final duration
    result.scan_duration = time.time() - start_time

    logger.info(
        "Async producer-consumer scan completed",
        path=str(path),
        files=result.file_count,
        dirs=result.dir_count,
        total_size=result.total_size,
        duration=f"{result.scan_duration:.2f}s"
    )

    return result


async def _walk_tree_async(
    root_path: Path,
    queue: asyncio.Queue[Union[Path, Tuple[str, Union[str, int]], None]],
    semaphore: asyncio.Semaphore,
    follow_symlinks: bool,
    *,
    max_depth: Optional[int] = None,
    exclude_patterns: Optional[List[str]] = None,
    min_size_bytes: int = 0,
    depth: int = 0
) -> None:
    """
    Producer task that walks directory tree and enqueues discovered items.

    Uses asyncio.to_thread for blocking filesystem operations while maintaining
    async coordination for concurrency control and cancellation.
    """
    logger.debug("Starting directory tree walker", root=str(root_path))

    dirs_to_process = [(root_path, depth)]

    while dirs_to_process:
        current_dir, current_depth = dirs_to_process.pop(0)

        # Check depth limit
        if max_depth is not None and current_depth >= max_depth:
            continue

        async with semaphore:
            try:
                # Use asyncio.to_thread for blocking directory listing
                entries = await asyncio.to_thread(_list_dir_entries, current_dir, follow_symlinks)

                # Filter entries based on exclude patterns
                if exclude_patterns:
                    filtered_entries = []
                    for entry_path, is_dir, size in entries:
                        if not _matches_exclude_patterns(entry_path, exclude_patterns):
                            filtered_entries.append((entry_path, is_dir, size))
                    entries = filtered_entries

                # Enqueue directory itself for counting
                await queue.put(current_dir)

                # Process entries and enqueue files immediately, collect subdirs
                subdirs = []
                for entry_path, is_dir, size in entries:
                    if is_dir:
                        subdirs.append((entry_path, current_depth + 1))
                    else:
                        # Filter by minimum size
                        if size >= min_size_bytes:
                            # Enqueue file info directly
                            await queue.put((str(entry_path), size))

                # Add subdirs to processing queue
                dirs_to_process.extend(subdirs)

            except Exception as e:
                # Enqueue error for consumer to handle
                await queue.put((str(current_dir), str(e)))
                logger.debug("Failed to process directory", path=str(current_dir), error=str(e))

    # Signal end of production
    await queue.put(None)  # type: ignore


async def _aggregate_results_async(
    queue: asyncio.Queue[Union[Path, Tuple[str, Union[str, int]], None]],
    result: ScanResult,
    progress_callback: Optional[Callable[[Path, Dict[str, Any]], Awaitable[None]]]
) -> None:
    """
    Consumer task that aggregates scan results from the queue.

    Processes enqueued items, updates result counters, and emits progress updates.
    """
    logger.debug("Starting result aggregator")

    while True:
        item = await queue.get()

        if item is None:
            # End of production signal
            break

        try:
            if isinstance(item, Path):
                # Directory discovered
                result.dir_count += 1
                if progress_callback:
                    await progress_callback(item, {
                        "type": "directory",
                        "path": str(item),
                        "dirs_found": result.dir_count,
                        "files_found": result.file_count
                    })

            elif isinstance(item, tuple) and len(item) == 2:
                item_path, item_data = item

                if isinstance(item_data, str):
                    # Error encountered
                    result.errors.append((item_path, item_data))
                    if progress_callback:
                        error_path = Path(item_path)
                        await progress_callback(error_path, {
                            "type": "error",
                            "path": item_path,
                            "error": item_data
                        })
                else:
                    # File with size (item_data is int)
                    result.file_count += 1
                    result.total_size += item_data  # type: ignore
                    result.files.append((item_path, item_data))  # type: ignore

                    # Emit progress update every 100 files or so
                    if result.file_count % 100 == 0 and progress_callback:
                        await progress_callback(Path(item_path), {
                            "type": "file_batch",
                            "files_found": result.file_count,
                            "total_size": result.total_size,
                            "last_file": item_path
                        })

        except Exception as e:
            logger.debug("Failed to process queue item", item=repr(item), error=str(e))

        finally:
            queue.task_done()

    logger.debug("Result aggregator completed", files=result.file_count, dirs=result.dir_count)


def _list_dir_entries(dir_path: Path, follow_symlinks: bool) -> List[Tuple[Path, bool, int]]:
    """
    Synchronous directory listing with metadata extraction.

    This function runs in a thread pool via asyncio.to_thread.
    Returns list of (path, is_dir, size) tuples.
    """
    entries = []

    try:
        for entry in os.scandir(dir_path):
            try:
                # Get basic info
                entry_path = Path(entry.path)
                is_dir = entry.is_dir(follow_symlinks=follow_symlinks)

                if is_dir:
                    # For directories, size is 0
                    size = 0
                else:
                    # For files, get size (may block on some filesystems)
                    try:
                        size = entry.stat(follow_symlinks=follow_symlinks).st_size
                    except (OSError, PermissionError):
                        size = 0

                entries.append((entry_path, is_dir, size))

            except (OSError, PermissionError) as e:
                # Skip entries we can't access
                logger.debug("Skipping inaccessible entry", path=entry.path, error=str(e))
                continue

    except (OSError, PermissionError) as e:
        logger.debug("Failed to list directory", path=str(dir_path), error=str(e))
        raise

    return entries


# Synchronous wrapper for backward compatibility
def scan_directory_sync(
    path: Path,
    *,
    max_depth: Optional[int] = None,
    exclude_patterns: Optional[List[str]] = None,
    min_size_bytes: int = 0,
    progress_callback: Optional[Callable[[Path, Any], Any]] = None,
    concurrency_limit: int = 10
) -> Dict[str, Any]:
    """
    Synchronous wrapper for scan_directory_async.

    This function provides backward compatibility for code expecting synchronous
    directory scanning. It automatically detects the execution context and
    uses the appropriate asyncio execution method to delegate to the new async implementation.

    .. deprecated::
        This function is provided for backward compatibility.
        New code should use the async scan_directory_async() function directly.

    Args:
        path: Root directory path to scan
        max_depth: Maximum directory depth to traverse (not supported in async version)
        exclude_patterns: List of glob patterns to exclude (not supported in async version)
        progress_callback: Optional progress callback function
        concurrency_limit: Maximum concurrent operations

    Returns:
        Dictionary containing scan results with keys:
        - 'total_size': Total bytes of all files
        - 'file_count': Total number of files
        - 'dir_count': Total number of directories
        - 'files': List of (path, size) tuples
        - 'errors': List of (path, error) tuples
    """
    import warnings
    warnings.warn(
        "scan_directory_sync is deprecated. Use scan_directory_async() async function instead.",
        DeprecationWarning,
        stacklevel=2
    )

    # Convert progress callback to async format if needed
    async_progress_callback: Optional[Callable[[Path, Dict[str, Any]], Awaitable[None]]] = None
    if progress_callback is not None:
        if asyncio.iscoroutinefunction(progress_callback):
            # Already async, use directly
            async_progress_callback = progress_callback  # type: ignore
        else:
            # Wrap sync callback to work with async interface
            async def async_progress_callback_wrapper(path: Path, data: Dict[str, Any]) -> None:
                try:
                    progress_callback(path, data)  # type: ignore
                except Exception as e:
                    logger.debug("Progress callback failed", path=str(path), error=str(e))
            async_progress_callback = async_progress_callback_wrapper

    try:
        # Check if we're in an async context
        loop = asyncio.get_running_loop()

        # We're in an async context - create a task and wait for it
        # This allows the async scan to run concurrently with other async operations
        task = loop.create_task(scan_directory_async(
            path,
            progress_callback=async_progress_callback
        ))
        result = loop.run_until_complete(task)

    except RuntimeError:
        # No event loop running - create one
        result = asyncio.run(scan_directory_async(
            path,
            progress_callback=async_progress_callback
        ))

    # Convert ScanResult back to legacy dict format for backward compatibility
    return {
        'total_size': result.total_size,
        'file_count': result.file_count,
        'dir_count': result.dir_count,
        'files': result.files,
        'errors': result.errors
    }