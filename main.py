"""
main.py
Entry point for NTEVietPatch.
Wires together: config, GitHubLoader, FilePatcher, and the Tkinter GUI.
"""

import json
import os
import sys
import threading
from pathlib import Path

from file_patcher import FilePatcher
from github_loader import GitHubLoader
from gui import NTEVietPatchGUI
import config as app_config

# ── Paths ─────────────────────────────────────────────────────────────── #
# When frozen by PyInstaller (--onefile), __file__ is inside a temp dir.
# We always want config/mods sitting next to the actual EXE.
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent

MODS_DIR   = BASE_DIR / "mods"
MODS_DIR.mkdir(exist_ok=True)


class App:
    """Application controller – owns config, loader, patcher, and GUI."""

    def __init__(self):
        # Constants from config.py
        self.constants = app_config
        
        # Initialize empty settings (we don't save/load settings.json anymore)
        self.settings = {}
        self.mods_dir = str(MODS_DIR)

        # Injected log function — will be replaced by GUI log after startup
        self._log_fn = print

        self.patcher = FilePatcher(self.settings, self.constants, log_fn=self._log)
        self.loader  = GitHubLoader(self.settings, self.constants)

        # Cached latest release
        self._latest_release: dict | None = None
        
    def _log(self, message: str) -> None:
        self._log_fn(message)

    def set_log_fn(self, fn) -> None:
        self._log_fn = fn
        self.patcher._log = fn  # propagate to patcher

    # ── Business logic ───────────────────────────────────────────────── #

    def check_update(self) -> tuple[bool, dict | None]:
        """Check GitHub for a newer release of the mod. Returns (available, release)."""
        current = self.settings.get("last_patched_version", "")
        available, release = self.loader.is_mod_update_available(current)
        if release:
            self._latest_release = release
        return available, release

    def download_release(self, release_data: dict, progress_cb=None) -> str:
        """
        Download and extract a specific GitHub release into mods/.
        Returns the path to the extracted directory.
        """
        if not release_data:
            raise RuntimeError("Dữ liệu phiên bản không hợp lệ.")

        return self.loader.download_and_extract(
            release_data,
            self.mods_dir,
            progress_cb=progress_cb,
        )

    def apply_patch(self, game_path: str, mod_source_dir: str, progress_cb=None, version_tag: str = "Unknown") -> None:
        """Apply mod files from `mod_source_dir` into `game_path`."""
        if not game_path or not os.path.isdir(game_path):
            raise FileNotFoundError(f"Thư mục game không hợp lệ: {game_path}")

        self.patcher.apply_patch(
            win64_path=game_path,
            mod_source_dir=mod_source_dir,
            progress_cb=progress_cb,
            version_tag=version_tag,
        )

    # ── Startup ──────────────────────────────────────────────────────── #

    def run(self) -> None:
        gui = NTEVietPatchGUI(self)

        # Wire GUI log function
        self.set_log_fn(gui.log)

        # Start the GUI event loop (this blocks)
        gui.run()

# ── Entry point ──────────────────────────────────────────────────────── #

def main():
    App().run()

if __name__ == "__main__":
    main()
