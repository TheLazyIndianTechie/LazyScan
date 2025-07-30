import os
import shutil
from unittest import TestCase, mock

class TestLazyScan(TestCase):

    def setUp(self):
        # Create a temporary directory to simulate cache directories
        self.test_dir = os.path.join(os.getcwd(), 'test_cache')
        os.makedirs(self.test_dir, exist_ok=True)

    def tearDown(self):
        # Clean up test directory after test
        shutil.rmtree(self.test_dir)

    @mock.patch('builtins.input', return_value='n')  # Mock user input to 'n' to avoid deletion
    @mock.patch('lazyscan.glob.glob')
    def test_clean_macos_cache(self, mock_glob, mock_input):
        """Test the clean_macos_cache function"""
        from lazyscan import clean_macos_cache

        # Mock cache paths - create real directories for test
        test_paths = []
        for i in range(3):
            path = os.path.join(self.test_dir, f'cache_{i}')
            os.makedirs(path, exist_ok=True)
            # Create a dummy file in each directory
            with open(os.path.join(path, 'dummy.txt'), 'w') as f:
                f.write('test data')
            test_paths.append(path)

        # Mock glob to return our test paths
        mock_glob.return_value = test_paths

        # Call the clean_macos_cache function with glob patterns
        total_freed = clean_macos_cache([os.path.join(self.test_dir, 'cache_*')], ('', '', '', '', ''))

        # Since we mocked input to 'n', nothing should be deleted
        self.assertEqual(total_freed, 0)
        
        # Verify directories still exist
        for path in test_paths:
            self.assertTrue(os.path.exists(path))

