import pytest
import tempfile
import os
from helpers.unity_cache_helpers import generate_unity_project_report

def create_fake_project(directory, size):
    """Create a fake Unity project structure with specified Library folder size."""
    library_path = os.path.join(directory, 'Library')
    os.makedirs(library_path)
    
    # Create dummy files to reach the specified size
    file_count = size // 1024
    for i in range(file_count):
        with open(os.path.join(library_path, f'dummy{i}.bin'), 'wb') as f:
            f.write(os.urandom(1024))  # 1 KB per file


@pytest.fixture

def mock_unity_projects(tmpdir):
    """Fixture to set up mock Unity projects."""
    project1 = tmpdir.mkdir('UnityProject1')
    create_fake_project(str(project1), size=2048)  # 2 KB

    project2 = tmpdir.mkdir('UnityProject2')
    create_fake_project(str(project2), size=4096)  # 4 KB

    return [str(project1), str(project2)]


def test_end_to_end_unity_reports(mock_unity_projects):
    """Test end-to-end Unity project cache analysis."""
    total_size = 0
    for project_path in mock_unity_projects:
        report = generate_unity_project_report(project_path)
        total_size += report['total_size']

    assert total_size == 6144  # 2 KB + 4 KB

