"""
Global pytest configuration and fixtures for LazyScan test suite.

This module provides shared fixtures and configuration for all test layers.
"""

import os
import tempfile
from pathlib import Path
from typing import Generator, Dict, Any
import pytest
import pyfakefs
from pyfakefs.fake_filesystem import FakeFilesystem


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Provide path to test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Provide a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_home(fs: FakeFilesystem) -> Path:
    """Provide a mock home directory with pyfakefs."""
    home_path = Path("/mock-home")
    fs.create_dir(home_path)
    
    # Set up common directories
    fs.create_dir(home_path / ".config" / "lazyscan")
    fs.create_dir(home_path / "Library" / "Caches")
    fs.create_dir(home_path / "Library" / "Application Support")
    fs.create_dir(home_path / ".cache")
    fs.create_dir(home_path / ".local" / "share")
    
    # Mock environment variables
    os.environ["HOME"] = str(home_path)
    os.environ["XDG_CACHE_HOME"] = str(home_path / ".cache")
    os.environ["XDG_CONFIG_HOME"] = str(home_path / ".config")
    
    return home_path


@pytest.fixture
def unity_mock_projects(fs: FakeFilesystem, mock_home: Path) -> Dict[str, Path]:
    """Create mock Unity projects for testing."""
    projects = {
        "TestGame1": mock_home / "Unity" / "TestGame1",
        "TestGame2": mock_home / "Unity" / "TestGame2"
    }
    
    for name, path in projects.items():
        # Create project structure
        fs.create_dir(path)
        fs.create_dir(path / "Assets")
        fs.create_dir(path / "Library" / "metadata")
        fs.create_dir(path / "Temp")
        fs.create_dir(path / "obj")
        fs.create_dir(path / "Logs")
        
        # Create some mock files with sizes
        fs.create_file(path / "Library" / "metadata" / "cache.db", st_size=1024 * 1024)  # 1MB
        fs.create_file(path / "Temp" / "temp_file.tmp", st_size=512 * 1024)  # 512KB
        fs.create_file(path / "Logs" / "Editor.log", st_size=256 * 1024)  # 256KB
    
    return projects


@pytest.fixture
def unreal_mock_projects(fs: FakeFilesystem, mock_home: Path) -> Dict[str, Path]:
    """Create mock Unreal Engine projects for testing."""
    projects = {
        "MyGame": mock_home / "Unreal Projects" / "MyGame",
        "TestProject": mock_home / "Unreal Projects" / "TestProject"
    }
    
    for name, path in projects.items():
        # Create project structure
        fs.create_dir(path)
        fs.create_dir(path / "Content")
        fs.create_dir(path / "Intermediate")
        fs.create_dir(path / "Saved" / "Logs")
        fs.create_dir(path / "Saved" / "Crashes")
        fs.create_dir(path / "DerivedDataCache")
        
        # Create mock files with sizes
        fs.create_file(path / "Intermediate" / "Build" / "cache.bin", st_size=2 * 1024 * 1024)  # 2MB
        fs.create_file(path / "Saved" / "Logs" / "MyGame.log", st_size=128 * 1024)  # 128KB
        fs.create_file(path / "DerivedDataCache" / "data.ddc", st_size=5 * 1024 * 1024)  # 5MB
    
    return projects


@pytest.fixture
def chrome_mock_profiles(fs: FakeFilesystem, mock_home: Path) -> Dict[str, Path]:
    """Create mock Chrome profiles for testing."""
    if os.name == 'nt':  # Windows
        chrome_base = mock_home / "AppData" / "Local" / "Google" / "Chrome"
    elif os.name == 'posix':
        if "darwin" in os.uname().sysname.lower():  # macOS
            chrome_base = mock_home / "Library" / "Application Support" / "Google" / "Chrome"
        else:  # Linux
            chrome_base = mock_home / ".config" / "google-chrome"
    else:
        chrome_base = mock_home / ".config" / "google-chrome"
    
    profiles = {
        "Default": chrome_base / "Default",
        "Profile 1": chrome_base / "Profile 1"
    }
    
    for name, path in profiles.items():
        # Create profile structure
        fs.create_dir(path)
        fs.create_dir(path / "Cache")
        fs.create_dir(path / "Code Cache")
        fs.create_dir(path / "GPUCache")
        fs.create_dir(path / "Service Worker")
        
        # Create mock cache files
        fs.create_file(path / "Cache" / "index", st_size=1024 * 1024)  # 1MB
        fs.create_file(path / "Code Cache" / "js" / "index", st_size=512 * 1024)  # 512KB
        fs.create_file(path / "GPUCache" / "data_0", st_size=256 * 1024)  # 256KB
    
    return profiles


@pytest.fixture
def mock_config_toml(fs: FakeFilesystem, mock_home: Path) -> Path:
    """Create a mock TOML configuration file."""
    config_path = mock_home / ".config" / "lazyscan" / "config.toml"
    config_content = """
[scanner]
recursive_depth = 10
follow_symlinks = false
exclude_patterns = [".git", ".svn", "node_modules"]

[deletion]
enable_backups = true
backup_location = "~/.lazyscan/backups"
audit_log_path = "~/.lazyscan/audit.json"
recovery_window_days = 30

[ui]
theme = "knight_rider"
animation_speed = 1.0
color_scheme = "dark"

[apps]
enabled_apps = ["unity", "unreal", "chrome"]
"""
    fs.create_file(config_path, contents=config_content)
    return config_path


@pytest.fixture
def sample_audit_log(fs: FakeFilesystem, mock_home: Path) -> Path:
    """Create a sample audit log file."""
    log_path = mock_home / ".lazyscan" / "audit.json"
    fs.create_dir(log_path.parent)
    log_content = """[
    {
        "timestamp": "2024-01-22T10:30:00Z",
        "operation": "scan",
        "user": "test_user",
        "paths_scanned": ["/mock-home/Unity/TestGame1"],
        "total_size": 1048576,
        "items_found": 3
    },
    {
        "timestamp": "2024-01-22T10:35:00Z",
        "operation": "delete",
        "user": "test_user",
        "paths_deleted": ["/mock-home/Unity/TestGame1/Temp"],
        "backup_id": "backup_20240122_103500",
        "space_freed": 524288
    }
]"""
    fs.create_file(log_path, contents=log_content)
    return log_path


# Platform-specific test markers
def pytest_runtest_setup(item):
    """Setup function to handle platform-specific test markers."""
    platform_markers = {
        'macos_only': 'darwin',
        'linux_only': 'linux', 
        'windows_only': 'win32'
    }
    
    for marker, platform in platform_markers.items():
        if item.get_closest_marker(marker) and not os.sys.platform.startswith(platform):
            pytest.skip(f"Test only runs on {platform}")


# Test data validation
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers and validate test structure."""
    for item in items:
        # Auto-add 'safe' marker for tests using pyfakefs
        if 'fs' in item.fixturenames:
            item.add_marker(pytest.mark.safe)
        
        # Auto-add test layer markers based on file path
        test_file = str(item.fspath)
        if '/unit/' in test_file:
            item.add_marker(pytest.mark.unit)
        elif '/integration/' in test_file:
            item.add_marker(pytest.mark.integration)
        elif '/e2e/' in test_file:
            item.add_marker(pytest.mark.e2e)


# Custom pytest command line options
def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-slow", action="store_true", default=False,
        help="run slow tests"
    )
    parser.addoption(
        "--run-unsafe", action="store_true", default=False,
        help="run tests that touch real filesystem (use with caution)"
    )


def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line("markers", "macos_only: mark test as macOS only")
    config.addinivalue_line("markers", "linux_only: mark test as Linux only")
    config.addinivalue_line("markers", "windows_only: mark test as Windows only")


def pytest_collection_modifyitems_v2(config, items):
    """Skip slow tests unless --run-slow is specified."""
    if config.getoption("--run-slow"):
        return
    
    skip_slow = pytest.mark.skip(reason="need --run-slow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)