"""
file_patcher.py
Handles: game-path detection, backup, and applying patches.

Target game : Neverness to Everness (CN / Global build)
Patch files : <dll_variant>, game_vi.dat, viet_font.ttf
  dll_variant = netbios.dll (Windows proxy DLL)
              = version.dll  (Linux / Proton proxy DLL)
Target dir  : <game_root>\\Client\\WindowsNoEditor\\HT\\Binaries\\Win64\\
"""

import datetime
import os
import shutil
import json
# winreg imported conditionally in methods
from pathlib import Path
from typing import Optional


# Root folder names to look for under Steam\common (or similar)
_GAME_FOLDER_NAMES = [
    "Neverness To Everness",
    "NevernessTOEverness",
    "Neverness to Everness",
]

# Common Linux game paths
_LINUX_GAME_PATHS = [
    "~/Games",
    "~/Lutris",
    "~/.wine/drive_c/Program Files",
    "~/.wine/drive_c/Program Files (x86)",
]



# --- Game & Mod Constants ---
_GAME_NAME = "Neverness to Everness"
_GAME_EXE = "HTGame.exe"
_GAME_EXE_ALT = "HTGame-Win64-Shipping.exe"
_GAME_SUBDIR = r"Client\WindowsNoEditor\HT\Binaries\Win64"
_MOD_FILES = ["netbios.dll", "version.dll", "game_vi.dat", "viet_font.ttf"]

class FilePatcher:
    def __init__(self, settings: dict, constants, log_fn=None):
        """
        :param settings: Loaded settings dict (from settings.json).
        :param constants: config.py module (still used for versions).
        :param log_fn: Optional callable(str) for logging messages to the UI.
        """
        self.settings = settings
        self.constants = constants
        self.game_exe: str = _GAME_EXE
        self.game_exe_alt: str = _GAME_EXE_ALT
        self.game_subdir: str = _GAME_SUBDIR
        self._log = log_fn or print

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _has_game_exe(self, directory: str) -> bool:
        """Return True if `directory` contains the game executable."""
        return (
            os.path.isfile(os.path.join(directory, self.game_exe))
            or os.path.isfile(os.path.join(directory, self.game_exe_alt))
        )

    def _resolve_win64_path(self, root: str) -> Optional[str]:
        """
        Given a candidate game *root* folder, return the Win64 directory if
        the game EXE is found either:
          - directly in root (user already pointed to Win64), or
          - in root + game_subdir.
        """
        if self._has_game_exe(root):
            return root

        candidate = os.path.join(root, self.game_subdir)
        if self._has_game_exe(candidate):
            return candidate

        return None

    # ------------------------------------------------------------------ #
    #  Game path detection                                                 #
    # ------------------------------------------------------------------ #

    def detect_game_path(self) -> Optional[str]:
        """
        Try multiple strategies to find the NTE Win64 directory.
        Returned path is the folder containing HTGame.exe (the patch target).
        """
        # 1. Config already has a path
        saved = self.settings.get("game_path", "").strip()
        if saved:
            resolved = self._resolve_win64_path(saved)
            if resolved:
                self._log(f"✔ Dùng đường dẫn đã lưu: {resolved}")
                return resolved

        # 2. Well-known default install path
        default = r"C:\Program Files\Neverness To Everness"
        resolved = self._resolve_win64_path(default)
        if resolved:
            self._log(f"✔ Tìm thấy tại vị trí mặc định: {resolved}")
            return resolved

        # 3. Windows Uninstall registry
        path = self._find_via_uninstall_registry()
        if path:
            return path

        # 5. Linux common paths
        from utils import is_linux
        if is_linux():
            path = self._find_via_linux_paths()
            if path:
                return path

        # 6. Scan all drives
        path = self._find_in_all_drives()
        if path:
            return path

        self._log("⚠ Không tìm thấy thư mục game tự động.")
        return None

    def _find_via_linux_paths(self) -> Optional[str]:
        for base in _LINUX_GAME_PATHS:
            full_base = os.path.expanduser(base)
            if not os.path.isdir(full_base):
                continue
            for name in _GAME_FOLDER_NAMES:
                root = os.path.join(full_base, name)
                resolved = self._resolve_win64_path(root)
                if resolved:
                    self._log(f"✔ Tìm thấy tại: {resolved}")
                    return resolved
        return None

    def _find_in_all_drives(self) -> Optional[str]:
        import string
        common_bases = [
            "",
            "Games",
            "Program Files",
            "Program Files (x86)",
        ]
        
        for d in string.ascii_uppercase:
            drive = f"{d}:\\"
            if not os.path.exists(drive):
                continue
                
            for base in common_bases:
                base_dir = os.path.join(drive, base)
                if not os.path.isdir(base_dir):
                    continue
                    
                for folder in _GAME_FOLDER_NAMES:
                    candidate = os.path.join(base_dir, folder)
                    if not os.path.isdir(candidate):
                        continue
                        
                    resolved = self._resolve_win64_path(candidate)
                    if resolved:
                        self._log(f"✔ Tìm thấy tại ổ đĩa: {resolved}")
                        return resolved
        return None

    def _find_via_uninstall_registry(self) -> Optional[str]:
        from utils import is_windows
        if not is_windows():
            return None
        import winreg
        search_bases = [
            (
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
            ),
            (
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
            ),
            (
                winreg.HKEY_CURRENT_USER,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
            ),
        ]
        keywords = [n.lower() for n in _GAME_FOLDER_NAMES] + ["neverness", "nte"]

        for hive, base_key in search_bases:
            try:
                with winreg.OpenKey(hive, base_key) as base:
                    for i in range(winreg.QueryInfoKey(base)[0]):
                        try:
                            sub_name = winreg.EnumKey(base, i)
                            with winreg.OpenKey(base, sub_name) as sub:
                                display_name, _ = winreg.QueryValueEx(sub, "DisplayName")
                                if any(kw in display_name.lower() for kw in keywords):
                                    location, _ = winreg.QueryValueEx(sub, "InstallLocation")
                                    resolved = self._resolve_win64_path(location)
                                    if resolved:
                                        self._log(
                                            f"✔ Tìm thấy qua registry Uninstall: {resolved}"
                                        )
                                        return resolved
                        except (OSError, FileNotFoundError):
                            continue
            except OSError:
                continue
        return None

    # ------------------------------------------------------------------ #
    #  Backup                                                              #
    # ------------------------------------------------------------------ #

    # ------------------------------------------------------------------ #
    #  Version Checking                                                    #
    # ------------------------------------------------------------------ #

    def get_installed_version(self, win64_path: str) -> Optional[dict]:
        """
        Check if the mod is installed in `win64_path`.
        Returns a dictionary with 'version' if found, else None.
        """
        v_file = os.path.join(win64_path, "nte_vietnamese_version.json")
        
        if os.path.exists(v_file):
            try:
                with open(v_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Check if the listed files actually exist in the game folder
                files = data.get("files", [])
                if files:
                    for fname in files:
                        if not os.path.exists(os.path.join(win64_path, fname)):
                            return None
                            
                return data
            except Exception:
                pass
                
        return None

    # ------------------------------------------------------------------ #
    #  Patch application                                                   #
    # ------------------------------------------------------------------ #

    # The two supported proxy-DLL names (GitHub releases ship with one or both)
    _DLL_WINDOWS = "netbios.dll"
    _DLL_LINUX   = "version.dll"

    def _active_dll_variant(self) -> str:
        """Return the DLL filename the user has selected (windows or linux)."""
        return self.settings.get("dll_variant", self._DLL_WINDOWS)

    def _build_file_map(self, mod_source_dir: str) -> dict[str, str]:
        """
        Walk `mod_source_dir` and build a mapping of
            dest_filename → absolute_source_path

        DLL variant logic
        -----------------
        The zip may contain only 'netbios.dll', only 'version.dll', or both.
        We always look for BOTH dll names, then rename/remap to whichever
        variant the user chose, so the correct filename is written into the
        game directory.

        Non-DLL files (game_vi.dat, viet_font.ttf) are copied as-is.
        """
        target_dll = self._active_dll_variant()
        other_dll  = self._DLL_LINUX if target_dll == self._DLL_WINDOWS else self._DLL_WINDOWS

        non_dll_files: list[str] = [
            f for f in _MOD_FILES
            if f not in (self._DLL_WINDOWS, self._DLL_LINUX)
        ]
        search_for = set(non_dll_files) | {target_dll, other_dll}

        # Gather all matching files first
        available_files: dict[str, str] = {}
        for root, _, files in os.walk(mod_source_dir):
            for fname in files:
                if fname in search_for:
                    available_files[fname] = os.path.join(root, fname)

        # dest_name → abs_src  (dest_name is what we write to the game dir)
        file_map: dict[str, str] = {}

        # 1. Map non-DLL files
        for fname in non_dll_files:
            if fname in available_files:
                file_map[fname] = available_files[fname]

        # 2. Map DLL variant
        if target_dll in available_files:
            # Exact match present (e.g. version 1.0.7+ has both)
            file_map[target_dll] = available_files[target_dll]
        elif other_dll in available_files:
            # Fallback (e.g. version <= 1.0.6 only has netbios.dll)
            file_map[target_dll] = available_files[other_dll]
            self._log(
                f"  ℹ Không tìm thấy {target_dll}, tự động đổi tên {other_dll} → {target_dll}"
            )

        return file_map

    def apply_patch(
        self,
        win64_path: str,
        mod_source_dir: str,
        progress_cb=None,
        version_tag: str = "Unknown",
    ) -> bool:
        """
        Copy mod files from `mod_source_dir` into `win64_path`.

        Respects `dll_variant` from config:
          - "netbios.dll"  → Windows (default)
          - "version.dll"  → Linux / Proton
        If the zip contains only the other variant it is automatically
        renamed to match the chosen variant.

        :returns: True on success.
        """
        target_dll = self._active_dll_variant()
        self._log(f"🔧 DLL variant: {target_dll}")

        file_map = self._build_file_map(mod_source_dir)

        if not file_map:
            raise FileNotFoundError(
                f"Không tìm thấy các file mod ({', '.join(_MOD_FILES)}) "
                f"trong thư mục: {mod_source_dir}"
            )

        self._log(f"📋 Tìm thấy {len(file_map)} file mod: {', '.join(file_map)}")

        # Copy into game Win64 dir
        total = len(file_map)
        for idx, (dest_name, src) in enumerate(file_map.items(), 1):
            dest = os.path.join(win64_path, dest_name)
            shutil.copy2(src, dest)
            self._log(f"  ✅ Áp dụng ({idx}/{total}): {dest_name}")
            if progress_cb:
                progress_cb(idx, total)
                
        # Write version file
        version_file = os.path.join(win64_path, "nte_vietnamese_version.json")
        try:
            with open(version_file, "w", encoding="utf-8") as f:
                json.dump({
                    "version": version_tag,
                    "patched_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "dll_variant": target_dll,
                    "app_version": getattr(self.constants, "APP_VERSION", "Unknown"),
                    "files": list(file_map.keys())
                }, f, ensure_ascii=False, indent=2)
            self._log(f"  📝 Đã lưu thông tin phiên bản JSON: {version_tag}")
        except Exception as e:
            self._log(f"  ⚠ Không thể lưu file version JSON: {e}")

        self._log("🎉 Patch đã được áp dụng thành công!")
        return True

    def remove_patch(self, win64_path: str, progress_cb=None) -> bool:
        """
        Remove installed mod files from `win64_path`.
        Uses nte_vietnamese_version.json to get the list of files to delete.
        """
        self._log("🗑 Bắt đầu gỡ cài đặt mod...")

        # 1. Try to get file list from version JSON
        version_file = os.path.join(win64_path, "nte_vietnamese_version.json")
        files_to_delete = []
        
        if os.path.exists(version_file):
            try:
                with open(version_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    files_to_delete = data.get("files", [])
            except Exception:
                pass
        
        # 2. Fallback to default list if JSON is missing or empty
        if not files_to_delete:
            target_dll = self._active_dll_variant()
            other_dll = self._DLL_LINUX if target_dll == self._DLL_WINDOWS else self._DLL_WINDOWS
            non_dll_files = [f for f in _MOD_FILES if f not in (self._DLL_WINDOWS, self._DLL_LINUX)]
            files_to_delete = non_dll_files + [target_dll, other_dll]
            
        # 3. Always include version files in deletion list
        if "nte_vietnamese_version.json" not in files_to_delete:
            files_to_delete.append("nte_vietnamese_version.json")
        
        total = len(files_to_delete)
        deleted_count = 0
        
        for idx, fname in enumerate(files_to_delete, 1):
            fpath = os.path.join(win64_path, fname)
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                    self._log(f"  ✅ Đã xóa: {fname}")
                    deleted_count += 1
                except Exception as e:
                    self._log(f"  ❌ Lỗi khi xóa {fname}: {e}")
            
            if progress_cb:
                progress_cb(idx, total)

        self._log(f"🎉 Gỡ cài đặt hoàn tất! Đã xóa {deleted_count} file.")
        return True
