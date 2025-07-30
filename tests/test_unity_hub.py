"""Unit tests for the Unity Hub parser module."""

import json
import tempfile
import unittest
from pathlib import Path

from helpers.unity_hub import read_unity_hub_projects


class TestUnityHubParser(unittest.TestCase):
    """Test cases for Unity Hub project parser."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temporary files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_read_valid_projects_json(self):
        """Test reading a valid Unity Hub projects JSON file."""
        # Create a fixture JSON file
        fixture_data = {
            "/Users/developer/Unity Projects/MyGame": {
                "name": "My Awesome Game",
                "version": "2022.3.10f1",
                "lastOpened": 1234567890
            },
            "/Volumes/External/UnityProjects/TestProject": {
                "version": "2021.3.15f1",
                "lastOpened": 1234567891
            },
            "/Users/developer/Documents/UnityDemo": {}
        }
        
        fixture_path = Path(self.temp_dir) / "projects-v1.json"
        with open(fixture_path, 'w') as f:
            json.dump(fixture_data, f)
        
        # Test reading the fixture
        projects = read_unity_hub_projects(str(fixture_path))
        
        # Verify results
        self.assertEqual(len(projects), 3)
        
        # Check first project (has name in metadata)
        project1 = next(p for p in projects if p['path'] == "/Users/developer/Unity Projects/MyGame")
        self.assertEqual(project1['name'], "My Awesome Game")
        
        # Check second project (no name in metadata, should use basename)
        project2 = next(p for p in projects if p['path'] == "/Volumes/External/UnityProjects/TestProject")
        self.assertEqual(project2['name'], "TestProject")
        
        # Check third project (empty metadata, should use basename)
        project3 = next(p for p in projects if p['path'] == "/Users/developer/Documents/UnityDemo")
        self.assertEqual(project3['name'], "UnityDemo")
    
    def test_missing_file(self):
        """Test behavior when JSON file is missing."""
        non_existent_path = Path(self.temp_dir) / "non_existent.json"
        projects = read_unity_hub_projects(str(non_existent_path))
        self.assertEqual(projects, [])
    
    def test_malformed_json(self):
        """Test behavior with malformed JSON."""
        fixture_path = Path(self.temp_dir) / "malformed.json"
        with open(fixture_path, 'w') as f:
            f.write("{ invalid json content")
        
        projects = read_unity_hub_projects(str(fixture_path))
        self.assertEqual(projects, [])
    
    def test_unexpected_json_structure(self):
        """Test behavior with unexpected JSON structure."""
        # Test with array instead of object
        fixture_path = Path(self.temp_dir) / "array.json"
        with open(fixture_path, 'w') as f:
            json.dump(["item1", "item2"], f)
        
        projects = read_unity_hub_projects(str(fixture_path))
        self.assertEqual(projects, [])
        
        # Test with nested but wrong structure
        fixture_path2 = Path(self.temp_dir) / "wrong_structure.json"
        with open(fixture_path2, 'w') as f:
            json.dump({"projects": [{"name": "test"}]}, f)
        
        projects = read_unity_hub_projects(str(fixture_path2))
        # Should still return empty list as it doesn't match expected structure
        self.assertEqual(len(projects), 0)
    
    def test_empty_json(self):
        """Test behavior with empty JSON object."""
        fixture_path = Path(self.temp_dir) / "empty.json"
        with open(fixture_path, 'w') as f:
            json.dump({}, f)
        
        projects = read_unity_hub_projects(str(fixture_path))
        self.assertEqual(projects, [])
    
    def test_default_path_behavior(self):
        """Test behavior when no path is provided (uses default)."""
        # This will likely return empty list since the default path
        # probably doesn't exist in test environment
        projects = read_unity_hub_projects()
        self.assertIsInstance(projects, list)
        # We can't assert much more without knowing the test environment
    
    def test_unicode_handling(self):
        """Test handling of Unicode characters in project names and paths."""
        fixture_data = {
            "/Users/developer/Unity/游戏项目": {
                "name": "我的游戏",
                "version": "2022.3.10f1"
            },
            "/Users/developer/Unity/Proyecto_Español": {
                "name": "Mi Juego Increíble",
                "version": "2021.3.15f1"
            }
        }
        
        fixture_path = Path(self.temp_dir) / "unicode.json"
        with open(fixture_path, 'w', encoding='utf-8') as f:
            json.dump(fixture_data, f, ensure_ascii=False)
        
        projects = read_unity_hub_projects(str(fixture_path))
        
        self.assertEqual(len(projects), 2)
        
        # Check Unicode handling
        chinese_project = next(p for p in projects if "游戏项目" in p['path'])
        self.assertEqual(chinese_project['name'], "我的游戏")
        
        spanish_project = next(p for p in projects if "Español" in p['path'])
        self.assertEqual(spanish_project['name'], "Mi Juego Increíble")


if __name__ == '__main__':
    unittest.main()
