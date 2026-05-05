"""
github_loader.py
Optimized GitHub integration with 2-level caching and rate-limit protection.
"""

import os
import json
import time
import threading
import shutil
import tempfile
import zipfile
import urllib.request
from typing import Callable, Optional, Dict, List, Any
from github import Github, Auth
from github.GithubException import GithubException, RateLimitExceededException

# --- GitHub Config ---
_MOD_REPO = "CallMeDangDev/NTE-Viet-Hoa"
_APP_REPO = "TanNhatCMS/NTEVietPatch"
_CACHE_TTL = 900  # 15 minutes


class GitHubLoader:
    def __init__(self, settings: dict, constants):
        self.settings = settings
        self.constants = constants
        
        # 1. Authentication Setup (Temporarily disabled token check)
        # token = os.getenv("GITHUB_TOKEN")
        # if token:
        #     auth = Auth.Token(token)
        #     self.g = Github(auth=auth, timeout=15)
        # else:
        self.g = Github(timeout=15)

        # 2. Cache Containers
        self._repo_objects = {}  # Cache for Repository objects
        self._mem_cache: Dict[str, Dict[str, Any]] = {}  # {repo_name: {"time": float, "data": list}}
        self._lock = threading.Lock()

    def _get_repo_object(self, repo_name: str):
        """Internal: Cache and return the PyGithub Repository object."""
        if repo_name not in self._repo_objects:
            try:
                self._repo_objects[repo_name] = self.g.get_repo(repo_name)
            except Exception as e:
                print(f"[Loader] Error getting repo {repo_name}: {e}")
                return None
        return self._repo_objects.get(repo_name)

    def _get_cache_path(self, repo_name: str) -> str:
        """Internal: Generate safe file path for JSON cache."""
        safe_name = repo_name.replace("/", "_").replace("\\", "_")
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), f"cache_{safe_name}.json")

    def _fetch_with_cache(self, repo_name: str, fetch_all: bool = False) -> List[Dict]:
        """
        Core logic: Memory -> File -> GitHub API -> File -> Memory.
        Handles RateLimitExceededException gracefully.
        """
        cache_path = self._get_cache_path(repo_name)
        now = time.time()

        with self._lock:
            # A. Try Memory Cache first
            if repo_name in self._mem_cache:
                m_cache = self._mem_cache[repo_name]
                if (now - m_cache["time"]) < _CACHE_TTL:
                    return m_cache["data"]

            # B. Try File Cache if memory is stale or empty
            file_data = None
            if os.path.exists(cache_path):
                try:
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        file_data = json.load(f)
                        # If file cache is still fresh, use it
                        if (now - os.path.getmtime(cache_path)) < _CACHE_TTL:
                            self._mem_cache[repo_name] = {"time": os.path.getmtime(cache_path), "data": file_data}
                            return file_data
                except Exception:
                    pass

        # C. Fetch from API (since both caches are stale or missing)
        try:
            repo = self._get_repo_object(repo_name)
            if not repo: raise ConnectionError("Cannot reach repository")

            if fetch_all:
                # Get all releases
                releases = [r.raw_data for r in repo.get_releases()]
            else:
                # Optimized: Only fetch latest release metadata
                latest = repo.get_latest_release()
                releases = [latest.raw_data]

            # Success: Save to File and Memory
            with self._lock:
                try:
                    with open(cache_path, 'w', encoding='utf-8') as f:
                        json.dump(releases, f, ensure_ascii=False, indent=2)
                except: pass
                self._mem_cache[repo_name] = {"time": now, "data": releases}
            
            return releases

        except (RateLimitExceededException, GithubException) as e:
            # D. Rate limit protection: Fallback to STALE cache if API fails
            if file_data:
                print(f"[Loader] Rate limited or API error. Falling back to stale cache for {repo_name}.")
                return file_data
            
            # If no cache at all, re-raise with friendly message
            if isinstance(e, RateLimitExceededException) or (hasattr(e, 'status') and e.status == 403):
                raise ConnectionError("GitHub API: Rate limit exceeded. No cache available. Try again later.")
            raise ConnectionError(f"GitHub API Error: {e}")

    # ── Public API ─────────────────────────────────────────────────── #

    def get_all_releases(self) -> List[Dict]:
        """Fetch all releases for the mod repo (with caching)."""
        return self._fetch_with_cache(_MOD_REPO, fetch_all=True)

    def get_latest_release(self) -> Optional[Dict]:
        """Fetch latest release metadata (optimized/cached)."""
        releases = self._fetch_with_cache(_MOD_REPO, fetch_all=False)
        return releases[0] if releases else None

    def is_mod_update_available(self, current_version: str) -> tuple[bool, Optional[Dict]]:
        """Check update available without full release iteration."""
        latest = self.get_latest_release()
        if not latest:
            return False, None
        
        latest_tag = latest.get("tag_name", "")
        if not current_version:
            return True, latest
            
        return (latest_tag != current_version), latest

    def is_app_update_available(self, current_version: str) -> tuple[bool, Optional[Dict]]:
        """Check for app (tool) updates."""
        releases = self._fetch_with_cache(_APP_REPO, fetch_all=False)
        if not releases:
            return False, None
            
        latest = releases[0]
        latest_tag = latest.get("tag_name", "")
        return (latest_tag != current_version), latest

    def download_release_assets(
        self,
        release_data: dict,
        dest_dir: str,
        progress_cb: Optional[Callable[[int, int], None]] = None,
    ) -> list[str]:
        """Download assets with local file existence check."""
        assets: list = release_data.get("assets", [])
        if not assets:
            zipball_url: str = release_data.get("zipball_url", "")
            if zipball_url:
                assets = [{"name": "source.zip", "browser_download_url": zipball_url}]

        if not assets:
            raise ValueError("No assets found in this release.")

        os.makedirs(dest_dir, exist_ok=True)
        downloaded_files: list[str] = []

        for asset in assets:
            url: str = asset.get("browser_download_url", "")
            name: str = asset.get("name", "asset")
            dest_path = os.path.join(dest_dir, name)

            # Optimization: Skip download if already exists (size check could be added for more safety)
            if os.path.exists(dest_path):
                print(f"[Loader] Asset already exists, skipping: {name}")
            else:
                self._download_file(url, dest_path, progress_cb)
            
            downloaded_files.append(dest_path)

        return downloaded_files

    def download_and_extract(self, release_data: dict, mods_dir: str, progress_cb=None) -> str:
        """Download assets and extract into a versioned directory."""
        tag = release_data.get("tag_name", "unknown")
        extract_to = os.path.join(mods_dir, tag)
        
        # Optimization: Do not re-download/extract if directory exists
        if os.path.isdir(extract_to):
            print(f"[Loader] Version {tag} already extracted.")
            return extract_to

        os.makedirs(extract_to, exist_ok=True)
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            files = self.download_release_assets(release_data, tmp_dir, progress_cb)
            for f in files:
                if f.endswith(".zip"):
                    with zipfile.ZipFile(f, 'r') as z:
                        z.extractall(extract_to)
                else:
                    shutil.copy2(f, extract_to)
                    
        return extract_to

    def _download_file(self, url: str, dest_path: str, progress_cb: Optional[Callable[[int, int], None]]):
        """Low-level download with progress reporting."""
        req = urllib.request.Request(url, headers={'User-Agent': 'NTEVietPatch-App'})
        with urllib.request.urlopen(req) as response:
            total_size = int(response.info().get('Content-Length', 0))
            block_size = 1024 * 8
            current_size = 0
            
            with open(dest_path, 'wb') as f:
                while True:
                    buffer = response.read(block_size)
                    if not buffer:
                        break
                    f.write(buffer)
                    current_size += len(buffer)
                    if progress_cb:
                        progress_cb(current_size, total_size)
