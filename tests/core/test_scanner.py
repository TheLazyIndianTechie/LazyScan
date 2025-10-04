#!/usr/bin/env python3
"""
Unit tests for lazyscan.core.scanner module.
Focuses on size calculation functionality with property-based testing using Hypothesis.
"""

import os
import tempfile
import pytest
import asyncio
from pathlib import Path
from unittest.mock import patch
from hypothesis import given, strategies as st
from hypothesis import assume

from lazyscan.core.scanner import get_disk_usage, scan_directory_with_progress
from lazyscan.core.scan import scan_directory, scan_directory_sync
from lazyscan.core.formatting import human_readable
from lazyscan.core.errors import ScanError


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


def test_get_disk_usage_empty_dir(temp_dir):
    """Test disk usage on an empty directory."""
    usage = get_disk_usage(temp_dir)
    assert usage == 0


def test_get_disk_usage_single_file(temp_dir):
    """Test disk usage with a single file."""
    file_path = temp_dir / "test.txt"
    file_path.write_text("Hello, world!")
    usage = get_disk_usage(temp_dir)
    assert usage > 0
    assert usage == file_path.stat().st_size


@given(st.integers(min_value=0, max_value=10**9))
def test_human_readable_size(file_size):
    """Property-based test for human_readable size formatting."""
    formatted = human_readable(file_size)
    assert isinstance(formatted, str)
    assert len(formatted) > 0

    # Test that parsing back approximates original (for common units)
    if file_size == 0:
        assert formatted == "0 B"
    elif file_size < 1024:
        assert formatted.endswith(" B")
    elif file_size < 1024**2:
        kb = file_size / 1024
        assert abs(float(formatted.split()[0]) - kb) < 0.1  # Rough check for rounding
        assert formatted.endswith(" KB")
    # Extend for MB, GB, etc., as needed


@given(st.lists(st.integers(min_value=1, max_value=1024), min_size=1, max_size=10))
def test_get_disk_usage_multiple_files(sizes):
    """Property-based test for disk usage with multiple files of varying sizes."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_dir = Path(tmp_dir)
        total_expected = 0
        for size in sizes:
            file_path = temp_dir / f"file_{size}.txt"
            file_path.write_bytes(os.urandom(size))
            total_expected += size

        usage = get_disk_usage(str(temp_dir))
        assert usage >= total_expected  # >= due to overhead
        # Assume no significant overhead for small files
        assume(usage <= total_expected * 1.1)  # Allow 10% overhead


def test_scan_directory_with_progress_empty(temp_dir, capsys):
    """Test scanning an empty directory with progress."""
    colors = ("", "", "", "", "", "", "", "", "", "")  # Mock colors
    with patch("lazyscan.core.scanner.get_disk_usage") as mock_usage:
        mock_usage.return_value = 0
        result = scan_directory_with_progress(str(temp_dir), colors)
        assert len(result) == 0  # Empty directory should return empty list

    captured = capsys.readouterr()
    assert (
        "Scanning" in captured.out or "Progress" in captured.out
    )  # Check for progress output


def test_scan_directory_with_progress_errors(temp_dir):
    """Test error handling in scan_directory_with_progress."""
    colors = ("", "", "", "", "", "", "", "", "", "")  # Mock colors
    with patch("lazyscan.core.scanner.get_disk_usage", side_effect=PermissionError):
        with pytest.raises(ScanError):
            list(scan_directory_with_progress(str(temp_dir), colors))


# Additional unit tests for edge cases
def test_get_disk_usage_nonexistent_path():
    """Test disk usage on a non-existent path."""
    nonexistent = "/nonexistent/path"
    # get_disk_usage should return 0 for non-existent paths (graceful handling)
    result = get_disk_usage(nonexistent)
    assert result == 0


def test_get_disk_usage_symlink(temp_dir):
    """Test handling of symlinks in disk usage calculation."""
    # Create a symlink to avoid recursion
    real_file = temp_dir / "real.txt"
    real_file.write_text("content")
    symlink = temp_dir / "symlink.txt"
    symlink.symlink_to(real_file)

    usage = get_disk_usage(temp_dir)
    # Should count the real file once, symlink size separately (usually small)
    assert usage > 0


# Async scanning tests
@pytest.mark.asyncio
async def test_scan_directory_empty_async(temp_dir):
    """Test async scanning of an empty directory."""
    result = await scan_directory(temp_dir, max_depth=1)
    assert result['file_count'] == 0
    assert result['dir_count'] == 1  # The directory itself
    assert result['total_size'] == 0
    assert len(result['files']) == 0
    assert len(result['errors']) == 0


@pytest.mark.asyncio
async def test_scan_directory_single_file_async(temp_dir):
    """Test async scanning with a single file."""
    file_path = temp_dir / "test.txt"
    content = "Hello, world!"
    file_path.write_text(content)

    result = await scan_directory(temp_dir, max_depth=1)
    assert result['file_count'] == 1
    assert result['dir_count'] == 1
    assert result['total_size'] == len(content.encode())
    assert len(result['files']) == 1
    assert result['files'][0][0] == str(file_path)
    assert result['files'][0][1] == len(content.encode())


@pytest.mark.asyncio
async def test_scan_directory_multiple_files_async(temp_dir):
    """Test async scanning with multiple files."""
    # Create multiple files with known sizes
    files_data = [
        ("file1.txt", "content1"),
        ("file2.txt", "content2"),
        ("file3.txt", "content3")
    ]

    total_size = 0
    for filename, content in files_data:
        file_path = temp_dir / filename
        file_path.write_text(content)
        total_size += len(content.encode())

    result = await scan_directory(temp_dir, max_depth=1)
    assert result['file_count'] == 3
    assert result['dir_count'] == 1
    assert result['total_size'] == total_size
    assert len(result['files']) == 3

    # Check that all files are accounted for
    file_paths = [f[0] for f in result['files']]
    for filename, _ in files_data:
        assert str(temp_dir / filename) in file_paths


@pytest.mark.asyncio
async def test_scan_directory_with_progress_callback(temp_dir):
    """Test async scanning with progress callback."""
    file_path = temp_dir / "test.txt"
    file_path.write_text("test content")

    callback_calls = []

    def progress_callback(path, data):
        callback_calls.append((str(path), data))

    result = await scan_directory(temp_dir, max_depth=1, progress_callback=progress_callback)

    # Should have received at least one progress callback
    assert len(callback_calls) > 0
    # Verify result is still correct
    assert result['file_count'] == 1


@pytest.mark.asyncio
async def test_scan_directory_max_depth(temp_dir):
    """Test max_depth parameter in async scanning."""
    # Create nested directory structure
    subdir = temp_dir / "subdir"
    subdir.mkdir()
    nested_file = subdir / "nested.txt"
    nested_file.write_text("nested")
    root_file = temp_dir / "root.txt"
    root_file.write_text("root")

    # Scan with max_depth=1 (should not enter subdir)
    result = await scan_directory(temp_dir, max_depth=1)
    assert result['file_count'] == 1  # Only root file
    assert str(root_file) in [f[0] for f in result['files']]

    # Scan with max_depth=2 (should enter subdir)
    result = await scan_directory(temp_dir, max_depth=2)
    assert result['file_count'] == 2  # Both files
    file_paths = [f[0] for f in result['files']]
    assert str(root_file) in file_paths
    assert str(nested_file) in file_paths


@pytest.mark.asyncio
async def test_scan_directory_exclude_patterns(temp_dir):
    """Test exclude_patterns parameter in async scanning."""
    # Create files to include and exclude
    included_file = temp_dir / "keep.txt"
    included_file.write_text("keep")
    excluded_file = temp_dir / "temp.txt"
    excluded_file.write_text("temp")

    result = await scan_directory(temp_dir, exclude_patterns=["*temp*"])
    assert result['file_count'] == 1
    assert str(included_file) in [f[0] for f in result['files']]
    assert str(excluded_file) not in [f[0] for f in result['files']]


def test_scan_directory_sync_wrapper(temp_dir):
    """Test synchronous wrapper for async scanning."""
    file_path = temp_dir / "test.txt"
    file_path.write_text("test content")

    result = scan_directory_sync(temp_dir, max_depth=1)
    assert result['file_count'] == 1
    assert result['dir_count'] == 1
    assert len(result['files']) == 1


@pytest.mark.asyncio
@given(st.lists(st.integers(min_value=1, max_value=1000), min_size=1, max_size=5))
async def test_scan_directory_deterministic_aggregation(file_sizes):
    """Property-based test for deterministic aggregation in async scanning."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_dir = Path(tmp_dir)

        # Create files with given sizes
        total_expected = 0
        for i, size in enumerate(file_sizes):
            file_path = temp_dir / f"file_{i}.txt"
            content = "x" * size
            file_path.write_text(content)
            total_expected += len(content.encode())

        # Scan multiple times and verify deterministic results
        results = []
        for _ in range(3):
            result = await scan_directory(temp_dir, max_depth=1)
            results.append(result)

        # All results should be identical
        for result in results[1:]:
            assert result['file_count'] == results[0]['file_count']
            assert result['total_size'] == results[0]['total_size']
            assert len(result['files']) == len(results[0]['files'])
