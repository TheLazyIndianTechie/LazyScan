#!/usr/bin/env python3
"""
Benchmarking and property-based tests for the async scanning engine.
Validates async vs sync behavior through targeted benchmarks and hypothesis-driven tests.
"""

import asyncio
import os
import tempfile
import time
from pathlib import Path
from typing import List, Tuple

import pytest
from hypothesis import given, strategies as st
from hypothesis import assume

from lazyscan.core.scan import scan_directory, scan_directory_sync, scan_directory_async
from lazyscan.core.scanner import scan_directory_with_progress


@pytest.fixture
def benchmark_temp_dir():
    """Create a temporary directory with test files for benchmarking."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_path = Path(tmp_dir)

        # Create a realistic directory structure
        create_test_directory_structure(temp_path, depth=3, files_per_dir=10, avg_file_size=1024)

        yield temp_path


def create_test_directory_structure(root: Path, depth: int, files_per_dir: int, avg_file_size: int):
    """Create a test directory structure with files."""
    if depth <= 0:
        return

    # Create files in current directory
    for i in range(files_per_dir):
        file_path = root / f"file_{i}.txt"
        # Vary file size around the average
        size_variation = avg_file_size // 4
        file_size = avg_file_size + (i * size_variation // files_per_dir) - size_variation // 2
        file_size = max(1, file_size)  # Ensure minimum size of 1 byte

        try:
            with open(file_path, 'wb') as f:
                f.write(os.urandom(file_size))
        except (OSError, PermissionError):
            # Skip if we can't write (e.g., permission issues)
            continue

    # Create subdirectories
    for i in range(min(3, depth)):  # Limit subdirs to avoid exponential growth
        subdir = root / f"subdir_{i}"
        try:
            subdir.mkdir(exist_ok=True)
            create_test_directory_structure(subdir, depth - 1, files_per_dir, avg_file_size)
        except (OSError, PermissionError):
            continue


@pytest.mark.benchmark
def test_async_vs_sync_performance(benchmark_temp_dir):
    """Benchmark async vs sync scanning performance."""
    colors = ("", "", "", "", "", "", "", "", "", "")  # Mock colors for sync test

    # Benchmark async scanning
    async def async_scan():
        return await scan_directory(benchmark_temp_dir, max_depth=2)

    async_result = asyncio.run(async_scan())

    # Benchmark sync scanning (legacy)
    def sync_scan():
        return scan_directory_with_progress(str(benchmark_temp_dir), colors)

    sync_result = sync_scan()

    # Verify results are equivalent
    assert async_result['file_count'] > 0
    assert len(sync_result) > 0

    # Calculate total size from sync result
    sync_total_size = sum(size for _, size in sync_result)
    assert abs(async_result['total_size'] - sync_total_size) < (async_result['total_size'] * 0.1)  # Allow 10% difference


@pytest.mark.asyncio
async def test_async_scan_correctness(benchmark_temp_dir):
    """Test that async scanning produces correct results."""
    result = await scan_directory(benchmark_temp_dir, max_depth=2)

    # Basic sanity checks
    assert result['file_count'] > 0
    assert result['dir_count'] > 0
    assert result['total_size'] > 0
    assert len(result['files']) == result['file_count']

    # Verify file sizes are reasonable
    for file_path, size in result['files']:
        assert size > 0
        assert os.path.exists(file_path)

    # Verify total size matches sum of individual files
    calculated_total = sum(size for _, size in result['files'])
    assert abs(result['total_size'] - calculated_total) < 100  # Allow small discrepancy


@pytest.mark.asyncio
async def test_scan_directory_async_vs_sync_consistency(benchmark_temp_dir):
    """Test that async and sync wrappers produce consistent results."""
    # Test async version
    async_result = await scan_directory_async(benchmark_temp_dir, follow_symlinks=False)

    # Test sync wrapper
    sync_result = scan_directory_sync(benchmark_temp_dir)

    # Compare results (allowing for some differences in metadata)
    assert async_result.file_count == sync_result['file_count']
    assert async_result.dir_count == sync_result['dir_count']
    assert abs(async_result.total_size - sync_result['total_size']) < 100  # Allow small differences
    assert len(async_result.files) == len(sync_result['files'])


@given(st.integers(min_value=1, max_value=100), st.integers(min_value=1, max_value=50))
@pytest.mark.asyncio
async def test_scan_directory_property_based(num_files, avg_size):
    """Property-based test for async directory scanning with varying file counts and sizes."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_path = Path(tmp_dir)

        # Create test files
        total_expected_size = 0
        for i in range(num_files):
            file_path = temp_path / f"test_file_{i}.txt"
            content = "x" * avg_size
            file_path.write_text(content)
            total_expected_size += len(content.encode())

        # Scan directory
        result = await scan_directory(temp_path, max_depth=1)

        # Verify results
        assert result['file_count'] == num_files
        assert result['dir_count'] == 1  # Just the root directory
        assert abs(result['total_size'] - total_expected_size) < 10  # Allow small encoding differences
        assert len(result['files']) == num_files


@given(st.integers(min_value=1, max_value=10), st.integers(min_value=1, max_value=5))
@pytest.mark.asyncio
async def test_scan_directory_nested_structure(num_dirs, depth):
    """Property-based test for nested directory structures."""
    assume(depth <= 3)  # Limit depth to avoid exponential test time

    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_path = Path(tmp_dir)

        # Create nested structure
        def create_nested_dirs(current_path: Path, remaining_depth: int):
            if remaining_depth <= 0:
                return 0, 0  # files, dirs

            total_files = 0
            total_dirs = 1  # Count current directory

            # Create some files in current directory
            for i in range(2):  # 2 files per directory
                file_path = current_path / f"file_{i}.txt"
                file_path.write_text(f"content_{i}")
                total_files += 1

            # Create subdirectories
            for i in range(min(2, num_dirs)):  # Limit subdirs
                subdir = current_path / f"subdir_{i}"
                subdir.mkdir(exist_ok=True)
                sub_files, sub_dirs = create_nested_dirs(subdir, remaining_depth - 1)
                total_files += sub_files
                total_dirs += sub_dirs

            return total_files, total_dirs

        expected_files, expected_dirs = create_nested_dirs(temp_path, depth)

        # Scan directory
        result = await scan_directory(temp_path, max_depth=depth + 1)

        # Verify results
        assert result['file_count'] == expected_files
        assert result['dir_count'] == expected_dirs


@pytest.mark.asyncio
async def test_scan_directory_error_handling():
    """Test error handling in async directory scanning."""
    # Test with non-existent directory
    with pytest.raises(ValueError, match="Path does not exist"):
        await scan_directory(Path("/nonexistent/path/that/does/not/exist"))

    # Test with file instead of directory
    with tempfile.NamedTemporaryFile() as tmp_file:
        with pytest.raises(ValueError, match="Path is not a directory"):
            await scan_directory(Path(tmp_file.name))


@pytest.mark.asyncio
async def test_scan_directory_concurrency():
    """Test that async scanning properly utilizes concurrency."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_path = Path(tmp_dir)

        # Create a directory with many subdirectories to test concurrency
        for i in range(10):
            subdir = temp_path / f"subdir_{i}"
            subdir.mkdir()
            for j in range(5):
                file_path = subdir / f"file_{j}.txt"
                file_path.write_text("x" * 100)

        start_time = time.time()
        result = await scan_directory(temp_path, max_depth=2, concurrency_limit=10)
        end_time = time.time()

        # Should complete reasonably quickly with concurrency
        duration = end_time - start_time
        assert duration < 5.0  # Should complete in less than 5 seconds

        # Verify results
        assert result['file_count'] == 50  # 10 subdirs * 5 files each
        assert result['dir_count'] == 11  # 10 subdirs + root


@pytest.mark.benchmark
@pytest.mark.parametrize("concurrency_limit", [1, 5, 10, 20])
@pytest.mark.asyncio
async def test_scan_directory_concurrency_scaling(benchmark_temp_dir, concurrency_limit):
    """Benchmark scanning performance with different concurrency limits."""
    start_time = time.time()
    result = await scan_directory(benchmark_temp_dir, max_depth=3, concurrency_limit=concurrency_limit)
    duration = time.time() - start_time

    # All concurrency levels should produce the same results
    assert result['file_count'] > 0
    assert result['total_size'] > 0

    # Higher concurrency should generally be faster (though not guaranteed in tests)
    # Just verify it completes successfully
    assert duration > 0


@pytest.mark.asyncio
async def test_scan_directory_progress_callback():
    """Test progress callback functionality in async scanning."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_path = Path(tmp_dir)

        # Create test files
        for i in range(5):
            file_path = temp_path / f"file_{i}.txt"
            file_path.write_text("x" * 100)

        callback_calls = []

        async def progress_callback(path: Path, data: dict):
            callback_calls.append((str(path), data))

        result = await scan_directory(temp_path, progress_callback=progress_callback)

        # Should have received progress callbacks
        assert len(callback_calls) > 0

        # Verify result correctness
        assert result['file_count'] == 5
        assert result['total_size'] == 500  # 5 files * 100 bytes each


@pytest.mark.asyncio
async def test_scan_directory_cancellation():
    """Test cancellation handling in async scanning."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_path = Path(tmp_dir)

        # Create a large directory structure
        create_test_directory_structure(temp_path, depth=4, files_per_dir=20, avg_file_size=2048)

        # Start scanning in a task
        task = asyncio.create_task(scan_directory(temp_path, max_depth=5))

        # Cancel after a short time
        await asyncio.sleep(0.1)
        task.cancel()

        # Should raise CancelledError
        with pytest.raises(asyncio.CancelledError):
            await task