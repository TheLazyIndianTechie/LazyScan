import pytest
from unittest import mock

# Since the selection parsing is part of prompt_unity_project_selection
# we'll test the selection logic more thoroughly

from lazyscan import prompt_unity_project_selection

class TestSelectionParser:
    """Test the selection parsing logic in prompt_unity_project_selection"""
    
    @mock.patch('sys.stdin.isatty', return_value=True)
    def test_single_selection(self, mock_isatty):
        """Test selecting a single project by number"""
        projects = [
            {'name': 'Project1', 'path': '/path/to/project1'},
            {'name': 'Project2', 'path': '/path/to/project2'},
            {'name': 'Project3', 'path': '/path/to/project3'},
        ]
        
        with mock.patch('builtins.input', return_value='2'):
            selected = prompt_unity_project_selection(projects)
            assert len(selected) == 1
            assert selected[0]['name'] == 'Project2'
    
    @mock.patch('sys.stdin.isatty', return_value=True)
    def test_multiple_selection_comma_separated(self, mock_isatty):
        """Test selecting multiple projects with comma separation"""
        projects = [
            {'name': 'Project1', 'path': '/path/to/project1'},
            {'name': 'Project2', 'path': '/path/to/project2'},
            {'name': 'Project3', 'path': '/path/to/project3'},
        ]
        
        with mock.patch('builtins.input', return_value='1,3'):
            selected = prompt_unity_project_selection(projects)
            assert len(selected) == 2
            assert selected[0]['name'] == 'Project1'
            assert selected[1]['name'] == 'Project3'
    
    @mock.patch('sys.stdin.isatty', return_value=True)
    def test_multiple_selection_space_separated(self, mock_isatty):
        """Test selecting multiple projects with space separation"""
        projects = [
            {'name': 'Project1', 'path': '/path/to/project1'},
            {'name': 'Project2', 'path': '/path/to/project2'},
            {'name': 'Project3', 'path': '/path/to/project3'},
        ]
        
        with mock.patch('builtins.input', return_value='2 3'):
            selected = prompt_unity_project_selection(projects)
            assert len(selected) == 2
            assert selected[0]['name'] == 'Project2'
            assert selected[1]['name'] == 'Project3'
    
    @mock.patch('sys.stdin.isatty', return_value=True)
    def test_select_all_projects(self, mock_isatty):
        """Test selecting all projects with 0"""
        projects = [
            {'name': 'Project1', 'path': '/path/to/project1'},
            {'name': 'Project2', 'path': '/path/to/project2'},
            {'name': 'Project3', 'path': '/path/to/project3'},
        ]
        
        with mock.patch('builtins.input', return_value='0'):
            selected = prompt_unity_project_selection(projects)
            assert len(selected) == 3
            assert selected == projects
    
    @mock.patch('sys.stdin.isatty', return_value=True)
    def test_quit_selection(self, mock_isatty):
        """Test quitting selection with 'q'"""
        projects = [
            {'name': 'Project1', 'path': '/path/to/project1'},
            {'name': 'Project2', 'path': '/path/to/project2'},
        ]
        
        with mock.patch('builtins.input', return_value='q'):
            selected = prompt_unity_project_selection(projects)
            assert selected == []
    
    @mock.patch('sys.stdin.isatty', return_value=True)
    def test_invalid_selection_then_valid(self, mock_isatty):
        """Test handling invalid input then valid selection"""
        projects = [
            {'name': 'Project1', 'path': '/path/to/project1'},
            {'name': 'Project2', 'path': '/path/to/project2'},
        ]
        
        # First return invalid input, then valid
        inputs = iter(['abc', '1'])
        with mock.patch('builtins.input', lambda *args: next(inputs)):
            selected = prompt_unity_project_selection(projects)
            assert len(selected) == 1
            assert selected[0]['name'] == 'Project1'
    
    @mock.patch('sys.stdin.isatty', return_value=True)
    def test_out_of_range_selection(self, mock_isatty):
        """Test handling out of range selection"""
        projects = [
            {'name': 'Project1', 'path': '/path/to/project1'},
            {'name': 'Project2', 'path': '/path/to/project2'},
        ]
        
        # Try to select project 5 (doesn't exist), then select valid project
        inputs = iter(['5', '2'])
        with mock.patch('builtins.input', lambda *args: next(inputs)):
            selected = prompt_unity_project_selection(projects)
            assert len(selected) == 1
            assert selected[0]['name'] == 'Project2'
    
    @mock.patch('sys.stdin.isatty', return_value=True)
    def test_mixed_valid_invalid_selection(self, mock_isatty):
        """Test mixed valid and invalid selections"""
        projects = [
            {'name': 'Project1', 'path': '/path/to/project1'},
            {'name': 'Project2', 'path': '/path/to/project2'},
            {'name': 'Project3', 'path': '/path/to/project3'},
        ]
        
        # Select 1, 5 (invalid), 3 - should only get 1 and 3
        with mock.patch('builtins.input', return_value='1,5,3'):
            selected = prompt_unity_project_selection(projects)
            assert len(selected) == 2
            assert selected[0]['name'] == 'Project1'
            assert selected[1]['name'] == 'Project3'
    
    @mock.patch('sys.stdin.isatty', return_value=True)
    def test_duplicate_selection(self, mock_isatty):
        """Test handling duplicate selections"""
        projects = [
            {'name': 'Project1', 'path': '/path/to/project1'},
            {'name': 'Project2', 'path': '/path/to/project2'},
        ]
        
        # Select same project multiple times
        with mock.patch('builtins.input', return_value='1,1,2,1'):
            selected = prompt_unity_project_selection(projects)
            # Should only have unique selections
            assert len(selected) == 2
            assert selected[0]['name'] == 'Project1'
            assert selected[1]['name'] == 'Project2'
    
    def test_non_interactive_terminal(self):
        """Test behavior when terminal is non-interactive"""
        projects = [
            {'name': 'Project1', 'path': '/path/to/project1'},
            {'name': 'Project2', 'path': '/path/to/project2'},
        ]
        
        with mock.patch('sys.stdin.isatty', return_value=False):
            selected = prompt_unity_project_selection(projects)
            assert selected == []
