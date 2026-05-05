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

class WorkerSignals(QObject):
    progress = Signal(int, int)
    log = Signal(str)
    status = Signal(str)
    finished = Signal(bool, str)
    releases_loaded = Signal(list)
    task_finished = Signal()
    install_finished = Signal() # New signal for success install
    update_progress_sig = Signal(int, int)
    request_cleanup = Signal()
    app_update_available = Signal(dict)
    error_occurred = Signal(str, str)

class NTEVietPatchGUI:
    def __init__(self, app_controller):
        self.app = app_controller
        self.qt_app = QApplication(sys.argv)
        self.qt_app.setStyle("Fusion")
        
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#f8fafc"))
        palette.setColor(QPalette.WindowText, QColor("#0f172a"))
        palette.setColor(QPalette.Base, QColor("#ffffff"))
        palette.setColor(QPalette.AlternateBase, QColor("#f1f5f9"))
        palette.setColor(QPalette.ToolTipBase, QColor("#ffffff"))
        palette.setColor(QPalette.ToolTipText, QColor("#0f172a"))
        palette.setColor(QPalette.Text, QColor("#0f172a"))
        palette.setColor(QPalette.Button, QColor("#ffffff"))
        palette.setColor(QPalette.ButtonText, QColor("#0f172a"))
        palette.setColor(QPalette.BrightText, QColor("#ef4444"))
        palette.setColor(QPalette.Highlight, QColor("#4f46e5"))
        palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
        self.qt_app.setPalette(palette)
        
        # Load QSS from theme.css
        self.qss_style = ""
        theme_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "theme.css")
        if os.path.exists(theme_path):
            try:
                with open(theme_path, "r", encoding="utf-8") as f:
                    self.qss_style = f.read()
                self.qt_app.setStyleSheet(self.qss_style)
            except Exception as e:
                print(f"Failed to load theme.css: {e}")
        
        # Set Application Icon (Taskbar)
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
        if os.path.exists(icon_path):
            app_icon = QIcon(icon_path)
            self.qt_app.setWindowIcon(app_icon)
            # Support for Windows Taskbar Icon
            from utils import set_windows_app_user_model_id
            set_windows_app_user_model_id(u"tannhat.ntevietpatch.tool.v1")
        
        self.window = QMainWindow()
        app_version = getattr(self.app.constants, 'APP_VERSION', '1.0.0')
        self.window.setWindowTitle(f"NTEVietPatch v{app_version} — Việt Hóa Neverness to Everness")
        self.window.resize(1100, 1000)
        
        if os.path.exists(icon_path):
            self.window.setWindowIcon(QIcon(icon_path))
        
        # Apply Windows Theme to Title Bar
        from utils import apply_windows_titlebar_theme
        apply_windows_titlebar_theme(self.window.winId(), dark_mode=False)
        
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
        self.signals.error_occurred.connect(self._on_task_error)
        
        self._releases_data = {}
        self._is_working = False
        
        # Pre-create Dashboard components
        self._build_ui()
        
        # Connect signal that depends on _warn_box (created in _build_ui)
        self.signals.install_finished.connect(self._show_warn_box)  # Show + resize on install success
        
        # Set initial compact size
        self.window.resize(1000, 480) 
        
        # Initial status check & update check
        QTimer.singleShot(500, self._check_installed_mod)
        QTimer.singleShot(1500, self._on_check_update)

    def _center_window(self):
        qr = self.window.frameGeometry()
        cp = self.qt_app.primaryScreen().availableGeometry().center()
        qr.moveCenter(cp)
        self.window.move(qr.topLeft())

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
        header.setStyleSheet("background-color: #ffffff; border-bottom: 1px solid #e2e8f0;")
        header.setFixedHeight(65)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(25, 0, 25, 0)

        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(2)

        title_label = QLabel("NTEVietPatch")
        title_label.setObjectName("HeaderTitle")
        title_label.setStyleSheet("font-size: 18px; font-weight: 900; color: #0f172a;")
        title_layout.addWidget(title_label)
        
        subtitle_label = QLabel("Việt Hóa Neverness to Everness")
        subtitle_label.setStyleSheet("font-size: 13px; color: #64748b;")
        title_layout.addWidget(subtitle_label)

        header_layout.addWidget(title_container)
        header_layout.addStretch()

        self._update_badge = QLabel("Kiểm tra...")
        self._update_badge.setObjectName("Badge")
        self._update_badge.setStyleSheet("background-color: #eef2ff; color: #4f46e5; padding: 4px 10px; border-radius: 6px; font-weight: 700; font-size: 11px;")
        header_layout.addWidget(self._update_badge)

        header_btns_container = QWidget()
        header_btns_layout = QHBoxLayout(header_btns_container)
        header_btns_layout.setContentsMargins(10, 0, 0, 0)
        header_btns_layout.setSpacing(8)

        self._btn_about = QPushButton("Giới thiệu")
        self._btn_about.setCursor(QCursor(Qt.PointingHandCursor))
        self._btn_about.clicked.connect(self._on_show_about)
        header_btns_layout.addWidget(self._btn_about)

        self._btn_log = QPushButton("Nhật ký")
        self._btn_log.setCursor(QCursor(Qt.PointingHandCursor))
        self._btn_log.clicked.connect(self._on_toggle_log)
        header_btns_layout.addWidget(self._btn_log)

        self._btn_update = QPushButton("Kiểm tra cập nhật")
        self._btn_update.setCursor(QCursor(Qt.PointingHandCursor))
        self._btn_update.clicked.connect(self._on_check_update)
        header_btns_layout.addWidget(self._btn_update)

        header_layout.addWidget(header_btns_container)
        main_layout.addWidget(header)

        # --- Content Area ---
        content_area = QWidget()
        content_area.setStyleSheet("background-color: #f8fafc;")
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Scrollable area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("MainScroll")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(40, 40, 40, 40)
        scroll_layout.setSpacing(24)

        # ── HERO SECTION ──────────────────────────────────────────────────
        main_card = QWidget()
        main_card.setObjectName("Card")
        main_layout_card = QVBoxLayout(main_card)
        main_layout_card.setContentsMargins(30, 30, 30, 30)
        main_layout_card.setSpacing(16)

        config_title = QLabel("CẤU HÌNH & TÙY CHỌN")
        config_title.setStyleSheet("color: #475569; font-weight: 800; font-size: 12px; letter-spacing: 1px;")
        main_layout_card.addWidget(config_title)

        path_row = QHBoxLayout()
        self._path_input = QLineEdit()
        self._path_input.setPlaceholderText("Vui lòng chọn thư mục Neverness To Everness")
        self._path_input.setText(self.app.settings.get("game_path", ""))
        self._path_input.textChanged.connect(self._on_path_changed)
        self._path_input.setContextMenuPolicy(Qt.CustomContextMenu)
        self._path_input.customContextMenuRequested.connect(self._show_path_context_menu)
        path_row.addWidget(self._path_input)

        browse_btn = QPushButton("Duyệt...")
        browse_btn.setCursor(QCursor(Qt.PointingHandCursor))
        browse_btn.clicked.connect(self._browse_game_path)
        path_row.addWidget(browse_btn)

        auto_btn = QPushButton("Tự động")
        auto_btn.setCursor(QCursor(Qt.PointingHandCursor))
        auto_btn.clicked.connect(self._auto_detect_path)
        path_row.addWidget(auto_btn)
        main_layout_card.addLayout(path_row)

        # Status inside Hero
        status_row = QHBoxLayout()
        self._installed_status_label = QLabel("Đang quét trạng thái...")
        self._installed_status_label.setStyleSheet("color: #334155; font-weight: 700; font-size: 15px;")
        status_row.addWidget(self._installed_status_label)
        
        self._details_btn = QPushButton("Chi tiết bản cài")
        self._details_btn.setStyleSheet("background: transparent; color: #4f46e5; border: none; font-weight: bold; text-decoration: underline;")
        self._details_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._details_btn.clicked.connect(self._on_show_installed_details)
        self._details_btn.hide()
        status_row.addWidget(self._details_btn)

        status_row.addStretch()

        self._remove_btn = QPushButton("Gỡ Cài Đặt")
        self._remove_btn.setObjectName("warning-btn")
        self._remove_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._remove_btn.clicked.connect(self._on_remove_mod)
        self._remove_btn.hide()
        status_row.addWidget(self._remove_btn)
        
        main_layout_card.addLayout(status_row)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("background-color: #f1f5f9; border: none; height: 1px; margin: 10px 0px;")
        main_layout_card.addWidget(divider)

        # ── BOTTOM CONTROLS CONTAINER (Hidden until game found) ──────────
        self._bottom_controls_container = QWidget()
        bottom_layout = QVBoxLayout(self._bottom_controls_container)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        split_layout = QHBoxLayout()
        split_layout.setSpacing(32)
        
        # LEFT COLUMN
        left_col = QVBoxLayout()
        left_col.setSpacing(16)
        
        ver_row = QHBoxLayout()
        ver_row.addWidget(QLabel("Phiên bản:"))
        from PySide6.QtWidgets import QListView
        self._ver_combo = QComboBox()
        self._ver_combo.setView(QListView())
        self._ver_combo.addItem("Chưa kiểm tra...")
        self._ver_combo.currentTextChanged.connect(self._on_version_selected)
        self._ver_combo.setEnabled(False) # Default disabled
        ver_row.addWidget(self._ver_combo)
        
        self._install_btn = QPushButton("🚀 Cài đặt")
        self._install_btn.setObjectName("accent-btn")
        self._install_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._install_btn.clicked.connect(self._on_download_patch)
        self._install_btn.setEnabled(False)
        self._install_btn.hide() # Default hidden
        ver_row.addWidget(self._install_btn)
        
        ver_row.addStretch()

        left_col.addLayout(ver_row)

        self._dll_group = QWidget()
        dll_layout = QHBoxLayout(self._dll_group)
        dll_layout.setContentsMargins(0, 0, 0, 0)
        dll_layout.addWidget(QLabel("Loại DLL:"))
        from PySide6.QtWidgets import QRadioButton, QButtonGroup
        self._dll_group_btns = QButtonGroup(self._dll_group)
        self._rb_netbios = QRadioButton("Windows (netbios.dll)")
        self._rb_version = QRadioButton("Linux / Proton (version.dll)")
        self._rb_netbios.setStyleSheet("color: #0f172a;")
        self._rb_version.setStyleSheet("color: #0f172a;")
        self._dll_group_btns.addButton(self._rb_netbios)
        self._dll_group_btns.addButton(self._rb_version)
        from utils import is_linux
        default_dll = "version.dll" if is_linux() else "netbios.dll"
        if self.app.settings.get("dll_variant", default_dll) == "version.dll":
            self._rb_version.setChecked(True)
        else:
            self._rb_netbios.setChecked(True)
        dll_layout.addWidget(self._rb_netbios)
        dll_layout.addWidget(self._rb_version)
        dll_layout.addStretch()
        left_col.addWidget(self._dll_group)
        self._dll_group.hide()
        
        left_col.addStretch()
        split_layout.addLayout(left_col, stretch=1)

        # RIGHT COLUMN: RELEASE NOTES
        self._notes_card = QWidget()
        notes_layout = QVBoxLayout(self._notes_card)
        notes_layout.setContentsMargins(0, 0, 0, 0)
        notes_layout.setSpacing(8)
        
        notes_title = QLabel("GHI CHÚ PHÁT HÀNH")
        notes_title.setStyleSheet("color: #475569; font-weight: 800; font-size: 12px; letter-spacing: 1px;")
        notes_layout.addWidget(notes_title)

        self._release_notes = QTextEdit()
        self._release_notes.setReadOnly(True)
        self._release_notes.setPlaceholderText("Nội dung thay đổi sẽ hiển thị ở đây...")
        self._release_notes.setFixedHeight(100) # Slightly shorter
        self._release_notes.setContextMenuPolicy(Qt.CustomContextMenu)
        self._release_notes.customContextMenuRequested.connect(self._show_notes_context_menu)
        notes_layout.addWidget(self._release_notes)
        
        split_layout.addWidget(self._notes_card, stretch=1)
        bottom_layout.addLayout(split_layout)
        self._bottom_controls_container.hide()
        main_layout_card.addWidget(self._bottom_controls_container)
        
        scroll_layout.addWidget(main_card)

        # ── PROGRESS & MESSAGES ───────────────────────────────────────────
        self._progress = QProgressBar()
        self._progress.setValue(0)
        self._progress.hide()
        scroll_layout.addWidget(self._progress)

        self._prog_label = QLabel("")
        self._prog_label.setStyleSheet("color: #64748b; font-size: 11px;")
        self._prog_label.hide()
        scroll_layout.addWidget(self._prog_label)

        # ── SYSTEM LOGS DIALOG ────────────────────────────────────────────
        from PySide6.QtWidgets import QDialog
        self._log_dialog = QDialog(self.window)
        self._log_dialog.setWindowTitle("Nhật ký hệ thống")
        self._log_dialog.resize(600, 400)
        self._log_dialog.setStyleSheet("background-color: #f8fafc;")
        log_dialog_layout = QVBoxLayout(self._log_dialog)
        log_dialog_layout.setContentsMargins(16, 16, 16, 16)
        
        self._log_box = QTextEdit()
        self._log_box.setReadOnly(True)
        log_dialog_layout.addWidget(self._log_box)

        scroll_layout.addStretch()

        scroll.setWidget(scroll_content)
        content_layout.addWidget(scroll)

        # ── BOTTOM STATUS BAR ─────────────────────────────────────────────
        self._status_label = QLabel("Sẵn sàng.")
        self._status_label.setObjectName("StatusBar")
        content_layout.addWidget(self._status_label)

        main_layout.addWidget(content_area)

    # ── Logic ────────────────────────────────────────────────────────── #

    def log(self, message: str):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self._log_box.append(f"[{timestamp}] {message}")
        self._log_box.moveCursor(QTextCursor.End)
        self._log_box.ensureCursorVisible()

    def _on_toggle_log(self):
        self._log_dialog.show()
        self._log_dialog.raise_()
        self._log_dialog.activateWindow()

    def _on_show_about(self):
        """Shows the introduction info in a popup dialog."""
        from PySide6.QtWidgets import QDialog
        dialog = QDialog(self.window)
        dialog.setWindowTitle("Giới thiệu")
        dialog.setFixedWidth(500)
        dialog.setMinimumHeight(450)
        dialog.setStyleSheet("background-color: #ffffff;")
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(15)
        
        title = QLabel("NTE Việt Hóa")
        title.setStyleSheet("font-size: 28px; font-weight: 900; color: #4f46e5;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("Bản Việt hoá không chính thức")
        subtitle.setStyleSheet("color: #64748b; font-size: 14px;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        
        layout.addSpacing(20)
        
        repo_mod = "CallMeDangDev/NTE-Viet-Hoa"
        repo_app = "TanNhatCMS/NTEVietPatch"
        
        sections = [
            ("Repository Việt Hóa (Mod Data)", f"https://github.com/{repo_mod}"),
            ("Repository Phần mềm (Tool App)", f"https://github.com/{repo_app}"),
            ("Discord hỗ trợ & thảo luận", "https://discord.gg/ARfX5gf8Wn"),
        ]
        
        for title_txt, url in sections:
            s_title = QLabel(title_txt)
            s_title.setStyleSheet("font-weight: 800; font-size: 13px; color: #1e293b; margin-top: 10px;")
            layout.addWidget(s_title)
            
            s_url = QPushButton(url)
            s_url.setStyleSheet("color: #4f46e5; text-align: left; background: transparent; border: none; text-decoration: underline; font-weight: 600; padding: 0;")
            s_url.setCursor(QCursor(Qt.PointingHandCursor))
            s_url.clicked.connect(lambda checked=False, u=url: self._open_url(u))
            layout.addWidget(s_url)
            
        layout.addStretch()
        
        ver = QLabel(f"Phiên bản Tool: {getattr(self.app.constants, 'APP_VERSION', '1.0.0')}")
        ver.setStyleSheet("color: #94a3b8; font-size: 11px;")
        ver.setAlignment(Qt.AlignCenter)
        layout.addWidget(ver)
        
        close_btn = QPushButton("Đóng")
        close_btn.setCursor(QCursor(Qt.PointingHandCursor))
        close_btn.clicked.connect(dialog.accept)
        
        # Inline style to ensure visibility
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #4f46e5;
                color: white;
                border: 1px solid #4338ca;
                border-radius: 8px;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #6366f1;
            }
        """)
        layout.addWidget(close_btn)
        
        dialog.exec()

    def _set_status(self, text: str):
        self._status_label.setText(text)

    @staticmethod
    def _fmt_size(n: int) -> str:
        """Format byte count to compact KB / MB string."""
        if n >= 1_048_576:
            return f"{n / 1_048_576:.1f} MB"
        if n >= 1_024:
            return f"{n / 1_024:.1f} KB"
        return f"{n} B"

    def _update_progress(self, current: int, total: int):
        if not self._is_working:
            return
        # Expand window on first appearance of progress bar
        if not self._progress.isVisible():
            if not getattr(self, "_progress_expanded", False):
                sz = self.window.size()
                self.window.resize(sz.width(), sz.height() + 70)
                self._progress_expanded = True
        self._progress.show()
        self._prog_label.show()
        pct = int((current / total) * 100) if total else 0
        self._progress.setValue(pct)
        if total > 0:
            self._prog_label.setText(
                f"{self._fmt_size(current)} / {self._fmt_size(total)}  ({pct}%)"
            )
        else:
            self._prog_label.setText(f"{self._fmt_size(current)}  ({pct}%)")
        self._prog_label.setStyleSheet("color: #7c3aed; font-weight: 600;")

    def _show_warn_box(self):
        """Show the post-install warning in a popup dialog."""
        msg = QMessageBox(self.window)
        from utils import apply_windows_titlebar_theme
        apply_windows_titlebar_theme(msg.winId(), dark_mode=False)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Hướng dẫn sau cài đặt")
        msg.setText("<b>🎉 Cài đặt hoàn tất!</b>")
        msg.setInformativeText(
            "1. Mở game bình thường, đợi ~10 giây để mod khởi động.<br>"
            "2. Hạn chế dùng Alt+F4 — hãy dùng menu thoát trong game để tránh lỗi lưu dữ liệu."
        )
        msg.setStyleSheet("QLabel { min-width: 400px; }")
        msg.exec()

    def _on_task_error(self, title, message):
        """Show error popup with log details."""
        msg = QMessageBox(self.window)
        from utils import apply_windows_titlebar_theme
        apply_windows_titlebar_theme(msg.winId(), dark_mode=False)
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle(title)
        msg.setText(f"<b>❌ Đã xảy ra lỗi:</b>")
        msg.setInformativeText("Vui lòng kiểm tra nhật ký chi tiết bên dưới để biết thêm thông tin.")
        msg.setDetailedText(message)
        msg.setStyleSheet("QLabel { min-width: 400px; }")
        msg.exec()

    def _show_path_context_menu(self, pos):
        menu = self._path_input.createStandardContextMenu()
        menu.setStyleSheet(self.qss_style)
        menu.exec(self._path_input.mapToGlobal(pos))

    def _show_notes_context_menu(self, pos):
        menu = self._release_notes.createStandardContextMenu()
        menu.setStyleSheet(self.qss_style)
        menu.exec(self._release_notes.mapToGlobal(pos))



    def _cleanup_task(self):
        """Final cleanup on UI thread after task is done."""
        self._is_working = False
        self._install_btn.setEnabled(True)
        self._progress.setVisible(False)
        self._prog_label.setVisible(False)
        self._progress.setValue(0)

        # Shrink window back if it was expanded for the progress bar
        if getattr(self, "_progress_expanded", False):
            sz = self.window.size()
            self.window.resize(sz.width(), sz.height() - 70)
            self._progress_expanded = False

        # Force the UI to process visibility changes
        QApplication.processEvents()

    def _check_installed_mod(self):
        path = self._path_input.text().strip()
        if not path:
            self._installed_status_label.setText("Chưa chọn thư mục")
            self._installed_status_label.setStyleSheet("color: #64748b; font-size: 14px;")
            self._remove_btn.setEnabled(False)
            self._details_btn.hide()
            self._v_info_cache = None
            self._bottom_controls_container.hide()
            return

        if not os.path.isdir(path):
            self._installed_status_label.setText("Thư mục không hợp lệ")
            self._installed_status_label.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 14px;")
            self._remove_btn.setEnabled(False)
            self._details_btn.hide()
            self._v_info_cache = None
            self._bottom_controls_container.hide()
            return

        # Show/Hide version selection container ONLY if game is detected
        is_game = self.app.patcher._has_game_exe(path)
        self._bottom_controls_container.setVisible(is_game)
        self._ver_combo.setEnabled(is_game)
        
        if not is_game:
            self._installed_status_label.setText("Không tìm thấy game tại đây")
            self._installed_status_label.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 14px;")
            self._remove_btn.setEnabled(False)
            self._details_btn.hide()
            self._v_info_cache = None
            return

        v_info = self.app.patcher.get_installed_version(path)
        self._v_info_cache = v_info
        if v_info:
            ver = v_info.get("version") or "Không rõ phiên bản"
            self._installed_status_label.setText(f"Đã cài — {ver}")
            self._installed_status_label.setStyleSheet("color: #16a34a; font-weight: bold; font-size: 14px;")
            self._remove_btn.show()
            self._remove_btn.setEnabled(True)
            self._details_btn.show()
        else:
            # Check if mod files exist without version file
            has_core = os.path.exists(os.path.join(path, "game_vi.dat")) and \
                       os.path.exists(os.path.join(path, "viet_font.ttf"))
            has_dll = os.path.exists(os.path.join(path, "netbios.dll")) or \
                      os.path.exists(os.path.join(path, "version.dll"))
            
            if has_core and has_dll:
                self._installed_status_label.setText("Đã cài — Phiên bản không xác định")
                self._installed_status_label.setStyleSheet("color: #d97706; font-weight: bold; font-size: 14px;")
                self._remove_btn.show()
                self._remove_btn.setEnabled(True)
                self._details_btn.hide()
            else:
                self._installed_status_label.setText("Chưa cài mod Việt Hóa")
                self._installed_status_label.setStyleSheet("color: #6b7280; font-weight: bold; font-size: 14px;")
                # If there are residual files, we still allow removal to clean up
                from file_patcher import _MOD_FILES
                has_any_residual = any(os.path.exists(os.path.join(path, f)) for f in _MOD_FILES)
                
                if has_any_residual:
                    self._remove_btn.show()
                    self._remove_btn.setEnabled(True)
                else:
                    self._remove_btn.hide()
                    
                self._details_btn.hide()

    def _on_path_changed(self):
        self._check_installed_mod()
        self.app.settings["game_path"] = self._path_input.text().strip()

    def _browse_game_path(self):
        dir_path = QFileDialog.getExistingDirectory(self.window, "Chọn thư mục cài game (ví dụ: Neverness To Everness)")
        if dir_path:
            # Tự động tìm thư mục Win64 từ thư mục gốc được chọn
            resolved = self.app.patcher._resolve_win64_path(dir_path)
            if resolved:
                self._path_input.setText(resolved)
            else:
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
            self._dll_group.setEnabled(False)
            self._install_btn.setEnabled(False)
            self._release_notes.clear()
            return

        self._install_btn.setEnabled(True)
        self._dll_group.setEnabled(True)
        
        data = self._releases_data.get(tag)
        if data:
            notes = data.get("body", "Không có ghi chú.")
            self._release_notes.setText(notes)
        else:
            self._release_notes.setText("Không tìm thấy dữ liệu cho phiên bản này.")


    def _on_check_update(self):
        self.log("🔍 Đang kiểm tra cập nhật...")
        self._set_status("Đang kiểm tra cập nhật...")
        self._btn_update.setEnabled(False)
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
            QTimer.singleShot(0, lambda: self._btn_update.setEnabled(True))

    def _on_version_selected(self, tag):
        if not tag or tag in ["Chưa kiểm tra...", "--- Chọn phiên bản ---"]:
            self._dll_group.setEnabled(False)
            self._install_btn.setEnabled(False)
            self._install_btn.hide()
            self._release_notes.clear()
            self._notes_card.hide()
            return

        self._notes_card.show()
        self._install_btn.show()
        self._install_btn.setEnabled(True)
        
        data = self._releases_data.get(tag)
        if data:
            body = data.get("body", "Không có ghi chú phát hành.")
            self._release_notes.setText(body)
            self._release_notes.moveCursor(QTextCursor.Start)

        # Logic for DLL Variant visibility (>= 1.0.7)
        clean = tag.replace("v", "").replace(" ", "")
        try:
            parts = tuple(int(x) for x in clean.split(".") if x.isdigit())
            if parts >= (1, 0, 7):
                self._dll_group.show()
                self._dll_group.setEnabled(True)
            else:
                self._dll_group.hide()
                self._rb_netbios.setChecked(True)
        except:
            self._dll_group.hide()

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
        self._set_status(f"Đã tải {len(tags)} phiên bản.")
        self._btn_update.setEnabled(True)
        
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
        from utils import apply_windows_titlebar_theme
        apply_windows_titlebar_theme(msg.winId(), dark_mode=False)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("✨ Cập nhật phần mềm")
        msg.setText(f"Đã có phiên bản mới của Tool NTE Viet-Hoa Patch: <b>{tag}</b>")
        msg.setInformativeText("Bạn có muốn mở trang tải về ngay bây giờ không?")
        msg.setDetailedText(body)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.Yes)
        
        # Sửa lỗi bị che nút bấm
        msg.setStyleSheet("QLabel { min-width: 450px; } QPushButton { min-width: 100px; }")
        
        if msg.exec() == QMessageBox.Yes:
            self._open_url(url)


    def _on_show_installed_details(self):
        path = self._path_input.text().strip()
        v_info = getattr(self, "_v_info_cache", None)
        if not v_info:
            v_info = self.app.patcher.get_installed_version(path)
        if not v_info:
            return

        tag = v_info.get("version") or "Không rõ"
        date = v_info.get("patched_at") or "Không rõ"
        dll = v_info.get("dll_variant") or "Không rõ"
        files = v_info.get("files", [])
        data = self._releases_data.get(tag)

        content = (
            f"<b>Phiên bản:</b> {tag}<br>"
            f"<b>Ngày cài:</b> {date}<br>"
            f"<b>DLL:</b> {dll}<br>"
            f"<b>Files:</b> {', '.join(files) if files else 'Không rõ'}<br><br>"
            "<b>--- GHI CHÚ PHÁT HÀNH ---</b><br><br>"
        )
        content += data.get("body", "Không có mô tả.") if data else "Chưa tải dữ liệu ghi chú."

        msg = QMessageBox(self.window)
        from utils import apply_windows_titlebar_theme
        apply_windows_titlebar_theme(msg.winId(), dark_mode=False)
        msg.setWindowTitle(f"Chi tiết bản cài: {tag}")
        msg.setTextFormat(Qt.RichText)
        msg.setText(content)
        msg.setStyleSheet("QLabel { min-width: 420px; }")
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
        from utils import apply_windows_titlebar_theme
        apply_windows_titlebar_theme(confirm.winId(), dark_mode=False)
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
            self.signals.install_finished.emit() # Trigger instructions
            self.signals.task_finished.emit()
        except Exception as e:
            err_details = f"Lỗi khi cài đặt: {e}\n\nĐường dẫn game: {game_path}\nPhiên bản: {data.get('tag_name')}"
            self.signals.error_occurred.emit("Lỗi cài đặt", err_details)
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
        from utils import apply_windows_titlebar_theme
        apply_windows_titlebar_theme(confirm.winId(), dark_mode=False)
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
            err_details = f"Lỗi khi gỡ mod: {e}\n\nĐường dẫn game: {path}"
            self.signals.error_occurred.emit("Lỗi gỡ mod", err_details)
            self.signals.log.emit(f"❌ Lỗi gỡ: {e}")
        finally:
            self.signals.request_cleanup.emit()

    def _update_progress_from_bg(self, c, t):
        self.signals.update_progress_sig.emit(c, t)

    def _open_url(self, url):
        import webbrowser
        webbrowser.open(url)
