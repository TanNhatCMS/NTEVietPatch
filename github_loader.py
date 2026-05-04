"""
github_loader.py
Handles all GitHub interactions: release checking, asset downloading.
"""

import json
import os
import shutil
import tempfile
import threading
import zipfile
import urllib.request
from typing import Callable, Optional
from github import Github
from github.GithubException import GithubException


class GitHubLoader:
    def __init__(self, settings: dict, constants):
        self.settings = settings
        self.constants = constants
        self.mod_repo_name = getattr(constants, "GITHUB_MOD_REPO", "CallMeDangDev/NTE-Viet-Hoa")
        self.app_repo_name = getattr(constants, "GITHUB_APP_REPO", "TanNhatCMS/NTEVietPatch")
        # Initialize Github without token (public access)
        self.g = Github(timeout=15)

    def get_all_releases(self) -> list[dict]:
        """Fetch all releases for the mod repo."""
        try:
            repo = self.g.get_repo(self.mod_repo_name)
            return [r.raw_data for r in repo.get_releases()]
        except Exception as e:
            raise ConnectionError(f"GitHub Error: {e}")

    def get_latest_release(self) -> Optional[dict]:
        """Fetch latest release metadata."""
        try:
            repo = self.g.get_repo(self.mod_repo_name)
            return repo.get_latest_release().raw_data
        except Exception:
            return None

    def is_mod_update_available(self, current_version: str) -> tuple[bool, Optional[dict]]:
        """Check if a mod update is available."""
        try:
            latest = self.get_latest_release()
            if not latest: return False, None
            latest_tag = latest.get("tag_name", "")
            if not current_version: return True, latest
            return (latest_tag != current_version), latest
        except Exception:
            return False, None

    def is_app_update_available(self, current_version: str) -> tuple[bool, Optional[dict]]:
        """Check if an app update is available."""
        try:
            repo = self.g.get_repo(self.app_repo_name)
            latest = repo.get_latest_release()
            return (latest.tag_name != current_version), latest.raw_data
        except Exception:
            return False, None

    def download_release_assets(
        self,
        release_data: dict,
        dest_dir: str,
        progress_cb: Optional[Callable[[int, int], None]] = None,
    ) -> list[str]:
        """
        Download all release assets (zip files) to `dest_dir`.
        Calls `progress_cb(bytes_downloaded, total_bytes)` if provided.
        Returns list of downloaded file paths.
        """
        assets: list = release_data.get("assets", [])
        if not assets:
            # Fallback: try zipball
            zipball_url: str = release_data.get("zipball_url", "")
            if zipball_url:
                assets = [{"name": "source.zip", "browser_download_url": zipball_url}]

        if not assets:
            raise ValueError("Bản phát hành này không có tệp đính kèm.")

        os.makedirs(dest_dir, exist_ok=True)
        downloaded_files: list[str] = []

        for asset in assets:
            url: str = asset.get("browser_download_url", "")
            name: str = asset.get("name", "asset")
            dest_path = os.path.join(dest_dir, name)

            self._download_file(url, dest_path, progress_cb)
            downloaded_files.append(dest_path)

        return downloaded_files

    def download_and_extract(
        self,
        release_data: dict,
        mods_dir: str,
        progress_cb: Optional[Callable[[int, int], None]] = None,
    ) -> str:
        """
        Download release zip and extract into `mods_dir`.
        Returns the path to the extracted folder.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            files = self.download_release_assets(release_data, tmp_dir, progress_cb)

            extract_root = os.path.join(mods_dir, release_data.get("tag_name", "latest"))
            os.makedirs(extract_root, exist_ok=True)

            for f in files:
                if f.endswith(".zip"):
                    with zipfile.ZipFile(f, "r") as zf:
                        zf.extractall(extract_root)
                else:
                    shutil.copy2(f, extract_root)

        return extract_root

    # ------------------------------------------------------------------ #
    #  Private helpers                                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _download_file(
        url: str,
        dest: str,
        progress_cb: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        req = urllib.request.Request(
            url, headers={"User-Agent": "NTEVietPatch/1.0"}
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 8192

                with open(dest, "wb") as fp:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        fp.write(chunk)
                        downloaded += len(chunk)
                        if progress_cb and total:
                            progress_cb(downloaded, total)
        except (urllib.error.URLError, urllib.error.HTTPError) as exc:
            raise ConnectionError(f"Tải xuống thất bại ({url}): {exc}") from exc
