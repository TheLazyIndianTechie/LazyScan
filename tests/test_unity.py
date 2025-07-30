import pytest
import json
import os
import shutil
from unittest import mock
from lazyscan import scan_unity_project_via_hub, prompt_unity_project_selection

@pytest.fixture
def create_mock_unity_hub_json(tmp_path):
    # Create a mock Unity Hub JSON file
    projects_data = {
        'recentProjects': [
            {'name': 'TestProject1', 'path': str(tmp_path / 'TestProject1')},
            {'name': 'TestProject2', 'path': str(tmp_path / 'TestProject2')}
        ]
    }
    json_path = tmp_path / 'mock_unity_hub.json'
    with open(json_path, 'w') as f:
        json.dump(projects_data, f)
    return json_path

@mock.patch('lazyscan.read_unity_hub_projects')
def test_scan_unity_project_via_hub(mock_read_projects, create_mock_unity_hub_json):
    mock_read_projects.return_value = [
        {'name': 'TestProject1', 'path': 'dummy/TestProject1'},
        {'name': 'TestProject2', 'path': 'dummy/TestProject2'}
    ]

    args = mock.Mock()
    args.unityhub_json = create_mock_unity_hub_json

    scan_unity_project_via_hub(args, clean=True)

    assert mock_read_projects.called

@mock.patch('sys.stdin.isatty', return_value=True)  # Mock interactive terminal
@mock.patch('builtins.input', return_value='1')
def test_prompt_unity_project_selection(mock_input, mock_isatty):
    projects = [
        {'name': 'TestProject1', 'path': 'dummy/TestProject1'},
        {'name': 'TestProject2', 'path': 'dummy/TestProject2'}
    ]

    selected = prompt_unity_project_selection(projects)
    
    assert len(selected) == 1
    assert selected[0]['name'] == 'TestProject1'
