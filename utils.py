"""
utils.py
Contains utility functions, OS detection, and system integrations.
"""

import sys
import os

def is_windows() -> bool:
    """Return True if the current OS is Windows."""
    return sys.platform == "win32"

def is_linux() -> bool:
    """Return True if the current OS is Linux."""
    return sys.platform.startswith("linux")

def is_macos() -> bool:
    """Return True if the current OS is macOS."""
    return sys.platform == "darwin"

def set_windows_app_user_model_id(app_id: str):
    """Sets the Application User Model ID for Windows Taskbar grouping."""
    if not is_windows():
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass

def apply_windows_titlebar_theme(window_id, dark_mode: bool = False):
    """
    Sets light or dark theme title bar on Windows 10/11.
    :param window_id: The HWND of the window (widget.winId())
    :param dark_mode: True for dark mode, False for light mode.
    """
    if not is_windows():
        return
    try:
        import ctypes
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
        rendering_policy = ctypes.c_int(1 if dark_mode else 0)
        set_window_attribute(
            int(window_id), 
            DWMWA_USE_IMMERSIVE_DARK_MODE, 
            ctypes.byref(rendering_policy), 
            ctypes.sizeof(rendering_policy)
        )
    except Exception:
        pass
