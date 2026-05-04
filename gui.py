import sys
import os
import json
import threading
import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QLineEdit, QComboBox, QProgressBar, 
    QTextEdit, QTabWidget, QGroupBox, QFileDialog, QMessageBox,
    QFrame, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, QSize, Signal, QObject, QThread, QTimer
from PySide6.QtGui import QFont, QIcon, QColor, QPalette, QCursor, QTextCursor

# --- Modern AI Dark QSS Style ---
QSS_STYLE = """
QMainWindow {
    background-color: #0b0e14;
}

QWidget {
    color: #cbd5e1;
    font-family: "Segoe UI", "Roboto", "Inter", sans-serif;
    font-size: 13px;
}

QGroupBox {
    background-color: #151921;
    border: 1px solid #232a35;
    border-radius: 16px;
    margin-top: 10px;
    padding-top: 20px;
    font-weight: bold;
    font-size: 14px;
    color: #00f2ff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 20px;
    padding: 0 10px;
}

QPushButton {
    background-color: #1e2530;
    border: 1px solid #2d3748;
    border-radius: 10px;
    padding: 10px 20px;
    font-weight: bold;
    color: #e2e8f0;
    min-width: 90px;
}

QPushButton:hover {
    background-color: #2d3748;
    border: 1px solid #4a5568;
}

QPushButton:pressed {
    background-color: #1a202c;
}

QPushButton#accent-btn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #00d2ff, stop:1 #3a7bd5);
    color: white;
    border: none;
}

QPushButton#accent-btn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #00e5ff, stop:1 #4a8df5);
}

QPushButton#warning-btn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ff4b2b, stop:1 #ff416c);
    color: white;
    border: none;
}

QPushButton#warning-btn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ff5f40, stop:1 #ff527d);
}

QLineEdit {
    background-color: #0d1117;
    border: 1px solid #232a35;
    border-radius: 8px;
    padding: 8px;
    color: #f8fafc;
    selection-background-color: #3182ce;
}

QComboBox {
    background-color: #0d1117;
    border: 1px solid #232a35;
    border-radius: 8px;
    padding: 8px;
    min-width: 160px;
}

QComboBox::drop-down {
    border: none;
}

QComboBox QAbstractItemView {
    background-color: #151921;
    border: 1px solid #232a35;
    selection-background-color: #2d3748;
    color: #cbd5e1;
}

QProgressBar {
    background-color: #0d1117;
    border: 1px solid #232a35;
    border-radius: 12px;
    text-align: center;
    height: 14px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00f2ff, stop:1 #7000ff);
    border-radius: 11px;
}

QTextEdit {
    background-color: #0d1117;
    border: 1px solid #232a35;
    border-radius: 12px;
    padding: 10px;
    font-family: "JetBrains Mono", "Consolas", monospace;
    color: #94a3b8;
}

QTabWidget::pane {
    border: none;
    background-color: #0b0e14;
}

QTabBar::tab {
    background-color: transparent;
    padding: 12px 35px;
    font-weight: bold;
    color: #64748b;
    font-size: 14px;
}

QTabBar::tab:selected {
    color: #00f2ff;
    border-bottom: 3px solid #00f2ff;
}

QTabBar::tab:hover {
    color: #e2e8f0;
}

QScrollBar:vertical {
    border: none;
    background: #0b0e14;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #1e2530;
    min-height: 30px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #2d3748;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QMessageBox {
    background-color: #151921;
    border: 1px solid #232a35;
}

QMessageBox QLabel {
    color: #cbd5e1;
}

QMessageBox QPushButton {
    background-color: #1e2530;
    border: 1px solid #2d3748;
    color: #e2e8f0;
    padding: 6px 20px;
    border-radius: 6px;
    min-width: 80px;
}

QMessageBox QPushButton:hover {
    background-color: #2d3748;
}
"""

class WorkerSignals(QObject):
    progress = Signal(int, int)
    log = Signal(str)
    status = Signal(str)
    finished = Signal(bool, str)
    releases_loaded = Signal(list)
    task_finished = Signal()
    update_progress_sig = Signal(int, int)
    request_cleanup = Signal()
    app_update_available = Signal(dict)

class NTEVietPatchGUI:
    def __init__(self, app_controller):
        self.app = app_controller
        self.qt_app = QApplication(sys.argv)
        self.qt_app.setStyleSheet(QSS_STYLE)
        
        # Set Application Icon (Taskbar)
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
        if os.path.exists(icon_path):
            app_icon = QIcon(icon_path)
            self.qt_app.setWindowIcon(app_icon)
            # Support for Windows Taskbar Icon
            if sys.platform == "win32":
                import ctypes
                myappid = u"tannhat.ntevietpatch.tool.v1"
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        
        self.window = QMainWindow()
        self.window.setWindowTitle("NTEVietPatch — Việt Hóa Neverness to Everness")
        self.window.resize(1100, 1000)
        
        if os.path.exists(icon_path):
            self.window.setWindowIcon(QIcon(icon_path))
        
        # Apply Windows Dark Mode to Title Bar
        self._apply_dark_title_bar(self.window)
        
        # Center window
        self._center_window()
        
        self.signals = WorkerSignals()
        self.signals.releases_loaded.connect(self._on_releases_loaded)
        self.signals.task_finished.connect(self._check_installed_mod)
        self.signals.log.connect(self.log)
        self.signals.status.connect(self._set_status)
        self.signals.update_progress_sig.connect(self._update_progress)
        self.signals.request_cleanup.connect(self._cleanup_task)
        self.signals.app_update_available.connect(self._on_app_update_found)
        
        self._releases_data = {}
        self._is_working = False
        
        self._build_ui()
        
        # Initial status check & update check
        QTimer.singleShot(500, self._check_installed_mod)
        QTimer.singleShot(1500, self._on_check_update)

    def _center_window(self):
        qr = self.window.frameGeometry()
        cp = self.qt_app.primaryScreen().availableGeometry().center()
        qr.moveCenter(cp)
        self.window.move(qr.topLeft())

    def _apply_dark_title_bar(self, widget):
        """Enables dark mode title bar on Windows 10/11."""
        if sys.platform != "win32":
            return
        try:
            import ctypes
            hwnd = widget.winId()
            # DWMWA_USE_IMMERSIVE_DARK_MODE = 20 (Windows 11 22000+)
            # DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19 (Windows 10 17763 to 19041)
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
            rendering_policy = ctypes.c_int(1)
            set_window_attribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(rendering_policy), ctypes.sizeof(rendering_policy))
        except Exception:
            pass

    def run(self):
        self.window.show()
        sys.exit(self.qt_app.exec())

    def _build_ui(self):
        main_widget = QWidget()
        self.window.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Header ---
        header = QFrame()
        header.setObjectName("Header")
        header.setStyleSheet("background-color: #151921; border-bottom: 1px solid #232a35;")
        header.setFixedHeight(75)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(25, 0, 25, 0)

        title_label = QLabel("🎮  NTE Việt Hóa")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #f8fafc;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        self._update_badge = QLabel("🆕 Kiểm tra...")
        self._update_badge.setStyleSheet("color: #00f2ff; font-weight: bold; margin-right: 15px;")
        header_layout.addWidget(self._update_badge)

        self._check_update_btn = QPushButton("🔍 Kiểm tra cập nhật")
        self._check_update_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._check_update_btn.clicked.connect(self._on_check_update)
        header_layout.addWidget(self._check_update_btn)

        main_layout.addWidget(header)

        # --- Tab Widget ---
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # ── Tab: Bảng Điều Khiển ───────────────────────────────────────── #
        dashboard_tab = QWidget()
        dashboard_outer_layout = QVBoxLayout(dashboard_tab)
        dashboard_outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        dashboard_layout = QVBoxLayout(scroll_content)
        dashboard_layout.setContentsMargins(20, 10, 20, 20)
        dashboard_layout.setSpacing(10)

        # ... (rest of dashboard widgets)

        # 1. Game Path Card
        group_path = QGroupBox(" 📁 Thư mục game ")
        path_layout = QVBoxLayout(group_path)
        
        path_input_row = QHBoxLayout()
        self._path_input = QLineEdit()
        self._path_input.setText(self.app.settings.get("game_path", ""))
        self._path_input.textChanged.connect(self._on_path_changed)
        path_input_row.addWidget(self._path_input)

        browse_btn = QPushButton("Duyệt…")
        browse_btn.clicked.connect(self._browse_game_path)
        path_input_row.addWidget(browse_btn)

        auto_btn = QPushButton("🔍 Tự động")
        auto_btn.clicked.connect(self._auto_detect_path)
        path_input_row.addWidget(auto_btn)
        
        path_layout.addLayout(path_input_row)
        dashboard_layout.addWidget(group_path)

        # Middle Row (2 Columns)
        middle_row = QHBoxLayout()
        middle_row.setSpacing(10)

        # 2. Installed Status Card (Left Column)
        self._group_status = QGroupBox(" 🛡 Trạng thái hiện tại ")
        self._group_status.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        status_main_layout = QVBoxLayout(self._group_status)
        
        status_row = QHBoxLayout()
        self._installed_status_label = QLabel("Đang quét trạng thái game...")
        self._installed_status_label.setStyleSheet("font-weight: bold; font-size: 15px;")
        status_row.addWidget(self._installed_status_label)

        self._details_btn = QPushButton("📄 Xem chi tiết bản này")
        self._details_btn.setObjectName("link-btn")
        self._details_btn.setStyleSheet("color: #4d69ff; text-decoration: underline; background: transparent; border: none; min-width: 0;")
        self._details_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._details_btn.clicked.connect(self._on_show_installed_details)
        self._details_btn.hide()
        status_row.addWidget(self._details_btn)
        status_row.addStretch()
        
        status_main_layout.addLayout(status_row)

        self._installed_info_label = QLabel("")
        self._installed_info_label.setStyleSheet("color: #9ca3af;")
        status_main_layout.addWidget(self._installed_info_label)

        self._installed_files_label = QLabel("")
        self._installed_files_label.setStyleSheet("font-family: 'Consolas'; font-size: 11px; color: #6b7280;")
        self._installed_files_label.setWordWrap(True)
        status_main_layout.addWidget(self._installed_files_label)

        btn_row_remove = QHBoxLayout()
        btn_row_remove.addStretch()
        self._remove_btn = QPushButton("🗑 Gỡ Cài Đặt Mod")
        self._remove_btn.setObjectName("warning-btn")
        self._remove_btn.setFixedWidth(200)
        self._remove_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._remove_btn.clicked.connect(self._on_remove_mod)
        self._remove_btn.setEnabled(False)
        btn_row_remove.addWidget(self._remove_btn)
        status_main_layout.addLayout(btn_row_remove)

        middle_row.addWidget(self._group_status)

        # 3. Update Card (Right Column)
        group_update = QGroupBox(" 📥 Cập nhật / Cài mới ")
        group_update.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        update_layout = QVBoxLayout(group_update)

        ver_row = QHBoxLayout()
        ver_row.addWidget(QLabel("Chọn phiên bản:"))
        self._ver_combo = QComboBox()
        self._ver_combo.addItem("Chưa kiểm tra...")
        self._ver_combo.currentTextChanged.connect(self._on_version_selected)
        ver_row.addWidget(self._ver_combo)
        
        self._ver_count_label = QLabel("")
        self._ver_count_label.setStyleSheet("color: #9ca3af;")
        ver_row.addWidget(self._ver_count_label)
        ver_row.addStretch()
        update_layout.addLayout(ver_row)

        self._release_notes = QTextEdit()
        self._release_notes.setReadOnly(True)
        self._release_notes.setPlaceholderText("Ghi chú phát hành sẽ hiện ở đây...")
        self._release_notes.setFixedHeight(120)
        update_layout.addWidget(self._release_notes)

        self._dll_group = QWidget()
        dll_layout = QHBoxLayout(self._dll_group)
        dll_layout.setContentsMargins(0, 0, 0, 0)
        dll_layout.addWidget(QLabel("DLL Variant:"))
        
        from PySide6.QtWidgets import QRadioButton, QButtonGroup
        self._dll_group_btns = QButtonGroup(self._dll_group)
        
        self._rb_netbios = QRadioButton("Windows — netbios.dll")
        self._rb_version = QRadioButton("Linux / Proton — version.dll")
        
        self._dll_group_btns.addButton(self._rb_netbios)
        self._dll_group_btns.addButton(self._rb_version)
        
        if self.app.settings.get("dll_variant", "netbios.dll") == "version.dll":
            self._rb_version.setChecked(True)
        else:
            self._rb_netbios.setChecked(True)
            
        dll_layout.addWidget(self._rb_netbios)
        dll_layout.addWidget(self._rb_version)
        dll_layout.addStretch()
        self._dll_group.hide()
        update_layout.addWidget(self._dll_group)

        # Action row for Installation inside this card
        btn_row_install = QHBoxLayout()
        btn_row_install.addStretch()
        self._install_btn = QPushButton("⬇ Tải & Cài Patch")
        self._install_btn.setObjectName("accent-btn")
        self._install_btn.setFixedWidth(200)
        self._install_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._install_btn.clicked.connect(self._on_download_patch)
        self._install_btn.setEnabled(False)
        btn_row_install.addWidget(self._install_btn)
        update_layout.addLayout(btn_row_install)

        middle_row.addWidget(group_update)
        dashboard_layout.addLayout(middle_row)

        # --- Progress ---
        self._progress = QProgressBar()
        self._progress.setValue(0)
        self._progress.hide()
        dashboard_layout.addWidget(self._progress)

        self._prog_label = QLabel("")
        self._prog_label.setStyleSheet("color: #6b7280; font-size: 11px;")
        self._prog_label.hide()
        dashboard_layout.addWidget(self._prog_label)

        # --- Warning (Post-Install Instructions) ---
        self._warn_box = QFrame()
        self._warn_box.setStyleSheet("background-color: #1a1612; border: 1px solid #3d2b1f; border-radius: 12px; padding: 12px;")
        warn_layout = QVBoxLayout(self._warn_box)
        
        w_title = QLabel("⚠ Sau khi cài patch, mở game bình thường.")
        w_title.setStyleSheet("color: #ff9800; font-weight: bold; font-size: 14px;")
        warn_layout.addWidget(w_title)
        
        w_body = QLabel(
            "Sau ~10 giây sẽ xuất hiện cửa sổ của mod, để nguyên trong lúc chơi.\n"
            "❌ Đừng dùng Alt+F4! Hãy dùng menu thoát trong game."
        )
        w_body.setStyleSheet("color: #f5c07a; font-size: 12px;")
        warn_layout.addWidget(w_body)
        self._warn_box.hide()
        dashboard_layout.addWidget(self._warn_box)

        # --- Log ---
        log_group = QGroupBox(" 📋 Nhật ký ")
        log_layout = QVBoxLayout(log_group)
        self._log_box = QTextEdit()
        self._log_box.setReadOnly(True)
        self._log_box.setMinimumHeight(60)
        self._log_box.setStyleSheet("color: #00f2ff; background-color: #0d1117; border: 1px solid #232a35;")
        log_layout.addWidget(self._log_box)
        dashboard_layout.addWidget(log_group)

        scroll.setWidget(scroll_content)
        dashboard_outer_layout.addWidget(scroll)
        self.tabs.addTab(dashboard_tab, "  🏠 Bảng Điều Khiển  ")

        # ── Tab: Giới Thiệu ────────────────────────────────────────── #
        about_tab = QWidget()
        about_layout = QVBoxLayout(about_tab)
        about_layout.setAlignment(Qt.AlignTop)
        about_layout.setContentsMargins(60, 40, 60, 40)

        a_title = QLabel("NTE Việt Hóa")
        a_title.setStyleSheet("font-size: 36px; font-weight: bold; color: #f8fafc;")
        a_title.setAlignment(Qt.AlignCenter)
        about_layout.addWidget(a_title)

        a_subtitle = QLabel("Neverness to Everness — Bản Việt hoá không chính thức")
        a_subtitle.setStyleSheet("color: #94a3b8; font-size: 15px;")
        a_subtitle.setAlignment(Qt.AlignCenter)
        about_layout.addWidget(a_subtitle)
        
        about_layout.addSpacing(40)

        repo_mod = getattr(self.app.constants, "GITHUB_MOD_REPO", "CallMeDangDev/NTE-Viet-Hoa")
        repo_app = getattr(self.app.constants, "GITHUB_APP_REPO", "TanNhatCMS/NTEVietPatchApp")

        sections = [
            ("📁 Repository Việt Hóa (Mod Data)", f"https://github.com/{repo_mod}"),
            ("🛠 Repository Phần mềm (Tool App)", f"https://github.com/{repo_app}"),
            ("💬 Discord hỗ trợ & thảo luận", "https://discord.gg/ARfX5gf8Wn"),
        ]

        for title, url in sections:
            s_title = QLabel(title)
            s_title.setStyleSheet("font-weight: bold; font-size: 15px; margin-top: 20px; color: #00f2ff;")
            about_layout.addWidget(s_title)
            
            s_url = QPushButton(url)
            s_url.setStyleSheet("color: #38bdf8; text-align: left; background: transparent; border: none; text-decoration: underline;")
            s_url.setCursor(QCursor(Qt.PointingHandCursor))
            s_url.clicked.connect(lambda checked=False, u=url: self._open_url(u))
            about_layout.addWidget(s_url)

        about_layout.addStretch()
        
        tool_ver = QLabel(f"Phiên bản Tool: {getattr(self.app.constants, 'APP_VERSION', '1.0.0')}")
        tool_ver.setStyleSheet("color: #64748b;")
        tool_ver.setAlignment(Qt.AlignCenter)
        about_layout.addWidget(tool_ver)

        self.tabs.addTab(about_tab, "  ℹ Giới Thiệu  ")

        # --- Status Bar ---
        self._status_label = QLabel("Sẵn sàng.")
        self._status_label.setStyleSheet("background-color: #1a1d2b; padding: 5px 15px; color: #6b7280; font-size: 11px;")
        main_layout.addWidget(self._status_label)

    # ── Logic ────────────────────────────────────────────────────────── #

    def log(self, message: str):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self._log_box.append(f"[{timestamp}] {message}")
        self._log_box.moveCursor(QTextCursor.End)
        self._log_box.ensureCursorVisible()

    def _set_status(self, text: str):
        self._status_label.setText(text)

    def _update_progress(self, current: int, total: int):
        if not self._is_working:
            return
        self._progress.show()
        self._prog_label.show()
        pct = int((current / total) * 100) if total else 0
        self._progress.setValue(pct)
        if total > 1000:
            self._prog_label.setText(f"{current:,} / {total:,} bytes  ({pct}%)")
        else:
            self._prog_label.setText(f"{current} / {total}  ({pct}%)")
        self._prog_label.setStyleSheet("color: #00f2ff;")

    def _cleanup_task(self):
        """Final cleanup on UI thread after task is done."""
        self._is_working = False
        self._install_btn.setEnabled(True)
        self._progress.setVisible(False)
        self._prog_label.setVisible(False)
        self._progress.setValue(0)
        # Force the UI to process visibility changes
        QApplication.processEvents()

    def _check_installed_mod(self):
        path = self._path_input.text().strip()
        if not path or not os.path.isdir(path):
            self._installed_status_label.setText("Thư mục không hợp lệ")
            self._installed_status_label.setStyleSheet("color: #6b7280; font-weight: bold;")
            self._installed_info_label.setText("Vui lòng chọn thư mục game HTGame/Binaries/Win64")
            self._installed_files_label.setText("")
            self._remove_btn.setEnabled(False)
            self._details_btn.hide()
            return

        v_info = self.app.patcher.get_installed_version(path)
        if v_info:
            ver = v_info.get("version", "Unknown")
            date = v_info.get("patched_at", "Unknown")
            dll = v_info.get("dll_variant", "Unknown")
            files = v_info.get("files", [])
            
            self._installed_status_label.setText(f"Phiên bản: {ver}")
            self._installed_status_label.setStyleSheet("color: #4caf50; font-weight: bold; font-size: 15px;")
            self._installed_info_label.setText(f"📅 Ngày cài: {date}    |    🔧 DLL: {dll}")
            self._installed_files_label.setText(f"📂 Files: {', '.join(files)}")
            self._remove_btn.setEnabled(True)
            self._details_btn.show()
            self._warn_box.show()
        else:
            self._installed_status_label.setText("Chưa cài mod Việt Hóa")
            self._installed_status_label.setStyleSheet("color: #6b7280; font-weight: bold;")
            self._installed_info_label.setText("Sẵn sàng cài đặt phiên bản mới.")
            self._installed_files_label.setText("")
            self._remove_btn.setEnabled(False)
            self._details_btn.hide()
            self._warn_box.hide()

    def _on_path_changed(self):
        self._check_installed_mod()
        self.app.settings["game_path"] = self._path_input.text().strip()

    def _browse_game_path(self):
        dir_path = QFileDialog.getExistingDirectory(self.window, "Chọn thư mục game (Win64)")
        if dir_path:
            self._path_input.setText(dir_path)

    def _auto_detect_path(self):
        self._set_status("Đang tìm thư mục game...")
        path = self.app.patcher.detect_game_path()
        if path:
            self._path_input.setText(path)
            self._set_status("Đã tìm thấy game!")
        else:
            self._set_status("Không tìm thấy game tự động.")
            QMessageBox.information(self.window, "Thông báo", "Không tìm thấy thư mục game tự động. Vui lòng duyệt thủ công.")

    def _on_version_selected(self, tag):
        if not tag or tag in ["Chưa kiểm tra...", "--- Chọn phiên bản ---"]:
            self._dll_group.hide()
            self._install_btn.setEnabled(False)
            self._release_notes.clear()
            return

        self._install_btn.setEnabled(True)
        self._dll_group.show()
        
        data = self._releases_data.get(tag)
        if data:
            notes = data.get("body", "Không có ghi chú.")
            self._release_notes.setText(notes)
        else:
            self._release_notes.setText("Không tìm thấy dữ liệu cho phiên bản này.")


    def _on_check_update(self):
        self.log("🔍 Đang kiểm tra cập nhật...")
        self._set_status("Đang kiểm tra cập nhật...")
        self._check_update_btn.setEnabled(False)
        threading.Thread(target=self._bg_check_update, daemon=True).start()

    def _bg_check_update(self):
        try:
            self.signals.log.emit("📡 Đang kết nối tới GitHub API...")
            # 1. Check App Update (Tool EXE)
            app_ver = getattr(self.app.constants, "APP_VERSION", "1.0.0")
            app_upd, app_release = self.app.loader.is_app_update_available(app_ver)
            if app_upd and app_release:
                tag = app_release.get("tag_name", "Unknown")
                self.signals.log.emit(f"✨ Phát hiện phiên bản Tool mới: {tag}")
                self.signals.app_update_available.emit(app_release)
            else:
                self.signals.log.emit("🚀 Phần mềm đang ở phiên bản mới nhất.")
            
            # 2. Check Mod Updates
            releases = self.app.loader.get_all_releases()
            if releases:
                self.signals.log.emit(f"✅ Đã tải danh sách {len(releases)} phiên bản Việt Hóa.")
                self.signals.releases_loaded.emit(releases)
            else:
                self.signals.log.emit("⚠ Không tìm thấy bản phát hành Việt Hóa nào.")
                self.signals.status.emit("Không tìm thấy bản phát hành mod.")
        except Exception as e:
            QTimer.singleShot(0, lambda: self._set_status(f"Lỗi: {e}"))
        finally:
            QTimer.singleShot(0, lambda: self._check_update_btn.setEnabled(True))

    def _on_releases_loaded(self, releases):
        """Called on main thread when releases are loaded."""
        self._releases_data = {r.get("tag_name", "unknown"): r for r in releases}
        tags = list(self._releases_data.keys())
        latest = tags[0] if tags else "N/A"
        
        self._ver_combo.clear()
        self._ver_combo.addItem("--- Chọn phiên bản ---")
        self._ver_combo.addItems(tags)
        self._ver_combo.setCurrentIndex(0)
        
        self._update_badge.setText(f"🆕 Mới nhất: {latest}")
        self._ver_count_label.setText(f"({len(tags)} bản)")
        self._set_status(f"Đã tải {len(tags)} phiên bản.")
        self._check_update_btn.setEnabled(True)
        
        # Log if a new mod version is available
        path = self._path_input.text().strip()
        v_info = self.app.patcher.get_installed_version(path)
        if v_info:
            current_ver = v_info.get("version", "")
            if latest != current_ver and current_ver != "Unknown":
                self.signals.log.emit(f"✨ Có bản Patch Việt Hóa mới: {latest} (Bạn đang dùng {current_ver})")
            else:
                self.signals.log.emit("💎 Bản Patch Việt Hóa của bạn đã là mới nhất.")
        else:
            self.signals.log.emit(f"💡 Sẵn sàng cài đặt phiên bản mới nhất: {latest}")
            
        # Reset UI for no selection
        self._on_version_selected("--- Chọn phiên bản ---")

    def _on_app_update_found(self, release):
        tag = release.get("tag_name", "Unknown")
        url = release.get("html_url", "")
        body = release.get("body", "Có phiên bản phần mềm mới.")
        
        msg = QMessageBox(self.window)
        self._apply_dark_title_bar(msg)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("✨ Cập nhật phần mềm")
        msg.setText(f"Đã có phiên bản mới của Tool NTE Viet-Hoa Patch: <b>{tag}</b>")
        msg.setInformativeText("Bạn có muốn mở trang tải về ngay bây giờ không?")
        msg.setDetailedText(body)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.Yes)
        
        if msg.exec() == QMessageBox.Yes:
            self._open_url(url)

    def _on_version_selected(self, tag):
        if not tag or tag in ["Chưa kiểm tra...", "--- Chọn phiên bản ---"]:
            self._dll_group.hide()
            self._install_btn.setEnabled(False)
            self._release_notes.clear()
            return

        self._install_btn.setEnabled(True)
        data = self._releases_data.get(tag)
        if data:
            self._release_notes.setText(data.get("body", "Không có mô tả."))
        
        # Logic >= 1.0.7
        clean = tag.replace("v", "").replace(" ", "")
        try:
            parts = tuple(int(x) for x in clean.split(".") if x.isdigit())
            if parts >= (1, 0, 7):
                self._dll_group.show()
            else:
                self._dll_group.hide()
                self._rb_netbios.setChecked(True)
        except:
            self._dll_group.hide()

    def _on_show_installed_details(self):
        path = self._path_input.text().strip()
        v_info = self.app.patcher.get_installed_version(path)
        if not v_info: return
        
        tag = v_info.get("version", "Unknown")
        data = self._releases_data.get(tag)
        
        content = f"<b>Phiên bản:</b> {tag}<br>"
        content += f"<b>Ngày cài:</b> {v_info.get('patched_at')}<br>"
        content += f"<b>DLL:</b> {v_info.get('dll_variant')}<br><br>"
        content += "--- GHI CHÚ PHÁT HÀNH ---<br><br>"
        content += data.get("body", "Không có mô tả.") if data else "Chưa tải dữ liệu ghi chú."
        
        msg = QMessageBox(self.window)
        self._apply_dark_title_bar(msg)
        msg.setWindowTitle(f"Chi tiết bản cài: {tag}")
        msg.setTextFormat(Qt.RichText)
        msg.setText(content)
        msg.setStyleSheet("QLabel { min-width: 400px; }")
        msg.exec()

    def _on_download_patch(self):
        game_path = self._path_input.text().strip()
        if not game_path:
            QMessageBox.warning(self.window, "Lỗi", "Vui lòng chọn thư mục game trước.")
            return
            
        tag = self._ver_combo.currentText()
        if tag in ["--- Chọn phiên bản ---", "Chưa kiểm tra..."]:
            QMessageBox.warning(self.window, "Lỗi", "Vui lòng chọn một phiên bản để cài đặt.")
            return
            
        data = self._releases_data.get(tag)
        if not data:
            self.log(f"❌ Không tìm thấy dữ liệu cho {tag}")
            return

        confirm = QMessageBox(self.window)
        self._apply_dark_title_bar(confirm)
        confirm.setIcon(QMessageBox.Question)
        confirm.setWindowTitle("Xác nhận")
        confirm.setText(f"Bắt đầu cài đặt phiên bản {tag}?")
        confirm.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        
        if confirm.exec() == QMessageBox.No: return

        self._install_btn.setEnabled(False)
        self._set_status(f"Đang tải {tag}...")
        
        self._is_working = True
        
        # Update DLL variant before start
        dll = "version.dll" if self._rb_version.isChecked() else "netbios.dll"
        self.app.settings["dll_variant"] = dll
        self.app.patcher.settings["dll_variant"] = dll

        self._progress.setValue(0)

        threading.Thread(target=self._bg_patch, args=(game_path, data), daemon=True).start()

    def _bg_patch(self, game_path, data):
        try:
            self.signals.log.emit(f"🔽 Tải xuống {data.get('tag_name')}...")
            extracted = self.app.download_release(data, progress_cb=self._update_progress_from_bg)
            
            self.signals.log.emit("🔧 Đang áp dụng patch...")
            self.app.apply_patch(game_path, extracted, progress_cb=self._update_progress_from_bg, version_tag=data.get('tag_name'))
            
            self.signals.status.emit("🎉 Patch thành công!")
            self.signals.task_finished.emit()
        except Exception as e:
            self.signals.log.emit(f"❌ Lỗi: {e}")
            self.signals.status.emit("Cài đặt thất bại.")
        finally:
            self.signals.request_cleanup.emit()

    def _on_remove_mod(self):
        path = self._path_input.text().strip()
        if not path:
            QMessageBox.warning(self.window, "Lỗi", "Vui lòng chọn thư mục game trước.")
            return
            
        confirm = QMessageBox(self.window)
        self._apply_dark_title_bar(confirm)
        confirm.setIcon(QMessageBox.Warning)
        confirm.setWindowTitle("Xác nhận gỡ")
        confirm.setText("Bạn có chắc chắn muốn gỡ mod?")
        confirm.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        if confirm.exec() == QMessageBox.No: return
        
        self._set_status("Đang gỡ mod...")
        self._is_working = True
        self._progress.setValue(0)
        
        threading.Thread(target=self._bg_remove, args=(path,), daemon=True).start()

    def _bg_remove(self, path):
        try:
            self.app.patcher.remove_patch(path, progress_cb=self._update_progress_from_bg)
            self.signals.status.emit("Gỡ mod thành công!")
            self.signals.task_finished.emit()
        except Exception as e:
            self.signals.log.emit(f"❌ Lỗi gỡ: {e}")
        finally:
            self.signals.request_cleanup.emit()

    def _update_progress_from_bg(self, c, t):
        self.signals.update_progress_sig.emit(c, t)

    def _open_url(self, url):
        import webbrowser
        webbrowser.open(url)
