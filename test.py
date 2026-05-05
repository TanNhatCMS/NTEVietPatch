import unittest
from unittest.mock import MagicMock, patch
import os
import json
import shutil
import subprocess
from github_loader import GitHubLoader

class TestNTEVietPatch(unittest.TestCase):
    def setUp(self):
        # Mock settings and constants
        self.settings = {}
        self.constants = MagicMock()
        self.constants.APP_VERSION = "1.0.0"
        
        # Initialize loader with mocked Github
        with patch('github_loader.Github') as mock_github:
            self.loader = GitHubLoader(self.settings, self.constants)
            self.mock_github_instance = mock_github.return_value

    def test_cache_logic(self):
        """Test if the loader correctly uses and creates cache files."""
        repo_name = "test/repo"
        cache_path = self.loader._get_cache_path(repo_name)
        
        # Ensure clean state
        if os.path.exists(cache_path):
            os.remove(cache_path)
            
        # Mock API response
        mock_repo = MagicMock()
        mock_release = MagicMock()
        mock_release.raw_data = {"tag_name": "v1.2.3"}
        mock_repo.get_latest_release.return_value = mock_release
        self.mock_github_instance.get_repo.return_value = mock_repo
        
        # 1. First fetch (should hit API and create cache)
        releases = self.loader._fetch_with_cache(repo_name)
        self.assertEqual(releases[0]["tag_name"], "v1.2.3")
        self.assertTrue(os.path.exists(cache_path))
        
        # 2. Second fetch (should hit memory cache)
        with patch.object(self.loader, '_get_repo_object') as mock_get_repo:
            releases2 = self.loader._fetch_with_cache(repo_name)
            self.assertEqual(releases2[0]["tag_name"], "v1.2.3")
            mock_get_repo.assert_not_called()

        # Cleanup
        if os.path.exists(cache_path):
            os.remove(cache_path)

    def test_version_check(self):
        """Test the logic for update detection."""
        # Mocking latest release as v1.1.0
        with patch.object(self.loader, 'get_latest_release') as mock_latest:
            mock_latest.return_value = {"tag_name": "v1.1.0"}
            
            # Case 1: Current is older
            available, release = self.loader.is_mod_update_available("v1.0.0")
            self.assertTrue(available)
            
            # Case 2: Current is same
            available, release = self.loader.is_mod_update_available("v1.1.0")
            self.assertFalse(available)

    def test_lint_code(self):
        """Run a basic lint check using flake8 if available."""
        print("\n[Lint] Running code quality check...")
        try:
            # Check if flake8 is installed
            subprocess.run(["flake8", "--version"], capture_output=True, check=True)
            
            # Run flake8 on the project
            result = subprocess.run(
                ["flake8", "gui.py", "main.py", "github_loader.py", "--max-line-length=120", "--ignore=E402,W503"],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                print("[Lint] Success: No major issues found.")
            else:
                print("[Lint] Warnings/Errors found:\n")
                print(result.stdout)
                # We don't fail the test suite for linting warnings unless requested
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("[Lint] Skipped: flake8 not found in environment.")

if __name__ == "__main__":
    unittest.main()
