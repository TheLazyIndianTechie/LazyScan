import pytest
import os
import tempfile
import shutil
from helpers.unity_cache_helpers import generate_unity_project_report

@pytest.fixture
def create_mock_unity_project(tmp_path):
    """Create a mock Unity project with Library and other cache directories"""
    project_path = tmp_path / "MockUnityProject"
    project_path.mkdir()
    
    # Create cache directories with dummy files
    library_dir = project_path / "Library"
    library_dir.mkdir()
    
    # Create some dummy files in Library
    (library_dir / "dummy1.asset").write_bytes(b"x" * 1024)  # 1KB
    (library_dir / "dummy2.asset").write_bytes(b"x" * 2048)  # 2KB
    
    # Create subdirectory in Library
    sub_dir = library_dir / "ShaderCache"
    sub_dir.mkdir()
    (sub_dir / "shader.cache").write_bytes(b"x" * 512)  # 0.5KB
    
    # Create Temp directory
    temp_dir = project_path / "Temp"
    temp_dir.mkdir()
    (temp_dir / "temp.file").write_bytes(b"x" * 256)  # 256B
    
    # Create obj directory
    obj_dir = project_path / "obj"
    obj_dir.mkdir()
    (obj_dir / "debug.obj").write_bytes(b"x" * 128)  # 128B
    
    # Create Logs directory
    logs_dir = project_path / "Logs"
    logs_dir.mkdir()
    (logs_dir / "console.log").write_bytes(b"x" * 64)  # 64B
    
    return project_path

def test_generate_unity_project_report_with_all_cache_dirs(create_mock_unity_project):
    """Test generating report for Unity project with all cache directories"""
    project_path = create_mock_unity_project
    
    report = generate_unity_project_report(
        str(project_path),
        "MockUnityProject",
        include_build=False
    )
    
    # Verify report structure
    assert report['name'] == "MockUnityProject"
    assert report['path'] == str(project_path)
    
    # Verify cache directories exist and have correct sizes
    assert report['cache_dirs']['Library']['exists'] is True
    assert report['cache_dirs']['Library']['size'] == 1024 + 2048 + 512  # 3584 bytes
    
    assert report['cache_dirs']['Temp']['exists'] is True
    assert report['cache_dirs']['Temp']['size'] == 256
    
    assert report['cache_dirs']['obj']['exists'] is True
    assert report['cache_dirs']['obj']['size'] == 128
    
    assert report['cache_dirs']['Logs']['exists'] is True
    assert report['cache_dirs']['Logs']['size'] == 64
    
    # Verify total size
    assert report['total_size'] == 3584 + 256 + 128 + 64  # 4032 bytes

def test_generate_unity_project_report_missing_directories():
    """Test generating report when some cache directories are missing"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_path = os.path.join(tmp_dir, "PartialProject")
        os.makedirs(project_path)
        
        # Only create Library directory
        library_dir = os.path.join(project_path, "Library")
        os.makedirs(library_dir)
        with open(os.path.join(library_dir, "test.file"), 'wb') as f:
            f.write(b"x" * 100)
        
        report = generate_unity_project_report(
            project_path,
            "PartialProject",
            include_build=False
        )
        
        # Verify Library exists
        assert report['cache_dirs']['Library']['exists'] is True
        assert report['cache_dirs']['Library']['size'] == 100
        
        # Verify other directories don't exist
        assert report['cache_dirs']['Temp']['exists'] is False
        assert report['cache_dirs']['obj']['exists'] is False
        assert report['cache_dirs']['Logs']['exists'] is False
        
        # Total should only include Library
        assert report['total_size'] == 100

def test_generate_unity_project_report_with_build_dir():
    """Test including Build directory in report"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_path = os.path.join(tmp_dir, "ProjectWithBuild")
        os.makedirs(project_path)
        
        # Create Build directory
        build_dir = os.path.join(project_path, "Build")
        os.makedirs(build_dir)
        with open(os.path.join(build_dir, "game.exe"), 'wb') as f:
            f.write(b"x" * 5000)
        
        report = generate_unity_project_report(
            project_path,
            "ProjectWithBuild",
            include_build=True
        )
        
        # Verify Build directory is included
        assert 'Build' in report['cache_dirs']
        assert report['cache_dirs']['Build']['exists'] is True
        assert report['cache_dirs']['Build']['size'] == 5000

def test_generate_unity_project_report_empty_project():
    """Test generating report for empty Unity project directory"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_path = os.path.join(tmp_dir, "EmptyProject")
        os.makedirs(project_path)
        
        report = generate_unity_project_report(
            project_path,
            "EmptyProject",
            include_build=False
        )
        
        # All directories should not exist
        for cache_name, cache_info in report['cache_dirs'].items():
            assert cache_info['exists'] is False
            assert cache_info['size'] == 0
        
        assert report['total_size'] == 0
