"""
Batch Add Games dialog for the Gaming Launcher.
Lets the user:
  1. Select multiple game executables at once via native file dialog
  2. Drag & drop executables, shortcuts (.lnk), or folders onto the dialog
  3. Review the list, edit display names, and add all at once

Cross-platform: Windows (.exe/.lnk), macOS (.app), Linux (executables).
Dependencies (Windows only):
  - pywin32 (pip install pywin32) — for resolving .lnk shortcuts
"""

import os
import sys
import stat
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QFrame, QScrollArea, QWidget, QLineEdit,
    QSizePolicy, QGridLayout
)
from PyQt6.QtGui import QPixmap, QPainter, QColor, QLinearGradient, QDragEnterEvent, QDropEvent
from PyQt6.QtCore import Qt, QMimeData


# ── Platform detection ─────────────────────────────────────────────────
IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")


def _resolve_lnk(lnk_path: str) -> str | None:
    """
    Resolve a Windows .lnk shortcut to its target executable path.
    Returns the target path if valid, or None if resolution fails.
    Only works on Windows (requires pywin32).
    """
    if not IS_WINDOWS:
        return None
    try:
        import pythoncom
        from win32com.shell import shell, shellcon

        # Create a ShellLink COM object
        link = pythoncom.CoCreateInstance(
            shell.CLSID_ShellLink, None,
            pythoncom.CLSCTX_INPROC_SERVER,
            shell.IID_IShellLink
        )
        # Load the .lnk file
        persist = link.QueryInterface(pythoncom.IID_IPersistFile)
        persist.Load(lnk_path)

        # Get the target path
        target_path, _ = link.GetPath(shell.SLGP_UNCPRIORITY)

        if target_path and os.path.isfile(target_path):
            return target_path
        return None
    except Exception as e:
        print(f"[BatchAdd] Failed to resolve shortcut '{lnk_path}': {e}")
        return None


def _is_executable(file_path: str) -> bool:
    """Check if a file is a valid executable on the current platform."""
    if not os.path.exists(file_path):
        return False

    lower = file_path.lower()

    if IS_WINDOWS:
        return lower.endswith('.exe')
    elif IS_MACOS:
        # .app bundles (directories) or Unix executables
        if lower.endswith('.app') and os.path.isdir(file_path):
            return True
        if os.path.isfile(file_path):
            return os.access(file_path, os.X_OK)
        return False
    else:
        # Linux: any file with execute permission
        if os.path.isfile(file_path):
            return os.access(file_path, os.X_OK)
        return False


def _resolve_file_path(file_path: str) -> str | None:
    """
    Given a file path, return the executable path.
    Cross-platform:
      - Windows: handles .exe files and .lnk shortcuts
      - macOS: handles .app bundles and Unix executables
      - Linux: handles files with execute permission
    """
    # Windows .lnk shortcut resolution
    if IS_WINDOWS and file_path.lower().endswith('.lnk'):
        target = _resolve_lnk(file_path)
        if target and _is_executable(target):
            return target
        return None

    # macOS .desktop symlinks (rare, but handle gracefully)
    if IS_LINUX and file_path.lower().endswith('.desktop'):
        # .desktop files are launchers, not executables — skip for now
        return None

    # Direct executable check
    if _is_executable(file_path):
        return file_path

    return None


def _get_file_filter() -> str:
    """Return the platform-appropriate file dialog filter string."""
    if IS_WINDOWS:
        return "Executables & Shortcuts (*.exe *.lnk);;Executables (*.exe);;Shortcuts (*.lnk);;All Files (*)"
    elif IS_MACOS:
        return "Applications (*.app);;All Files (*)"
    else:
        return "All Files (*)"


def _get_drop_hint() -> str:
    """Return the platform-appropriate drag & drop hint text."""
    if IS_WINDOWS:
        return (
            "📂  Drag & drop .exe files or shortcuts here\n"
            "or click \"Browse\" to select multiple files"
        )
    elif IS_MACOS:
        return (
            "📂  Drag & drop .app bundles here\n"
            "or click \"Browse\" to select applications"
        )
    else:
        return (
            "📂  Drag & drop game executables here\n"
            "or click \"Browse\" to select files"
        )


def _clean_exe_name(path: str) -> str:
    """Extract a clean display name from an executable path."""
    # Handle macOS .app bundles: use the bundle name
    if path.lower().endswith('.app'):
        basename = os.path.basename(path).replace('.app', '')
    else:
        basename = os.path.splitext(os.path.basename(path))[0]
    # Remove common engine/build suffixes
    for suffix in [
        "-Win64-Shipping", "_x64", "_x86", "-Win64",
        "-Win32", "_dx11", "_dx12", "_vulkan", "-Shipping",
        "_BE", "_EAC", "Launcher", "launcher"
    ]:
        basename = basename.replace(suffix, "")
    return basename.replace("_", " ").replace("-", " ").strip().title()



class _GameRow(QWidget):
    """A single row in the batch list showing exe path + editable name + optional cover."""

    def __init__(self, exe_path: str, accent: str, parent=None):
        super().__init__(parent)
        self._exe_path = exe_path
        self._accent = accent

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(10)

        # Remove button
        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(28, 28)
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.setStyleSheet(
            "background: #CC3333; color: white; border: none; "
            "border-radius: 14px; font-weight: 700; font-size: 12px;"
        )
        remove_btn.clicked.connect(self._on_remove)
        layout.addWidget(remove_btn)

        # Info column
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        # Editable name
        self._name_input = QLineEdit(_clean_exe_name(exe_path))
        self._name_input.setStyleSheet("font-weight: 600; font-size: 13px;")
        self._name_input.setPlaceholderText("Game name...")
        info_layout.addWidget(self._name_input)

        # Path label
        path_label = QLabel(exe_path)
        path_label.setStyleSheet("font-size: 11px; color: #666677;")
        path_label.setWordWrap(True)
        info_layout.addWidget(path_label)

        layout.addLayout(info_layout, stretch=1)
        
        # Separator line at bottom
        self.setStyleSheet(
            "border-bottom: 1px solid #222233; background: transparent;"
        )

    def _on_remove(self):
        """Remove this row from the parent layout."""
        self.setParent(None)
        self.deleteLater()

    @property
    def exe_path(self) -> str:
        return self._exe_path
        
    @property
    def game_name(self) -> str:
        return self._name_input.text().strip() or _clean_exe_name(self._exe_path)


class BatchAddDialog(QDialog):
    """
    Modal dialog for adding multiple games at once.
    Supports multi-file selection and drag & drop of .exe files/folders.
    """

    def __init__(self, accent: str = "#00D4FF", parent=None):
        super().__init__(parent)
        self._accent = accent
        self._rows: list[_GameRow] = []

        self.setWindowTitle("Batch Add Games")
        self.setMinimumSize(560, 480)
        self.resize(600, 520)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        # Enable drag & drop
        self.setAcceptDrops(True)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # Title
        title = QLabel("BATCH ADD GAMES")
        title.setStyleSheet(
            f"font-size: 20px; font-weight: 700; color: {self._accent};"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #222233;")
        sep.setFixedHeight(1)
        layout.addWidget(sep)

        # Drop zone hint (platform-specific text)
        self._drop_zone = QLabel(_get_drop_hint())
        self._drop_zone.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._drop_zone.setStyleSheet(
            f"border: 2px dashed {self._accent}44; "
            f"border-radius: 12px; padding: 20px; "
            f"color: #8888AA; font-size: 14px; "
            f"background: #0D0D1A; min-height: 60px;"
        )
        layout.addWidget(self._drop_zone)

        # Browse button
        browse_row = QHBoxLayout()
        browse_row.addStretch()

        browse_btn = QPushButton("  Browse Executables...")
        browse_btn.setFixedHeight(36)
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.clicked.connect(self._browse_exe_files)
        browse_row.addWidget(browse_btn)

        browse_folder_btn = QPushButton("  Scan Folder...")
        browse_folder_btn.setFixedHeight(36)
        browse_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_folder_btn.setToolTip("Scan a folder for game executables")
        browse_folder_btn.clicked.connect(self._browse_folder)
        browse_row.addWidget(browse_folder_btn)

        browse_row.addStretch()
        layout.addLayout(browse_row)

        # Game list (scroll area)
        self._list_label = QLabel("0 games selected")
        self._list_label.setStyleSheet(
            "font-size: 13px; font-weight: 600; color: #8888AA;"
        )
        layout.addWidget(self._list_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self._list_container = QWidget()
        self._list_container.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(2)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self._list_container)

        layout.addWidget(scroll, stretch=1)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        clear_btn = QPushButton("Clear All")
        clear_btn.setFixedHeight(36)
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.clicked.connect(self._clear_all)
        btn_row.addWidget(clear_btn)

        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(36)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        add_btn = QPushButton("Add All Games")
        add_btn.setObjectName("accentBtn")
        add_btn.setFixedHeight(36)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self._on_add_all)
        btn_row.addWidget(add_btn)

        layout.addLayout(btn_row)

    # ── Drag & Drop ────────────────────────────────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Accept drags with file URLs."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._drop_zone.setStyleSheet(
                f"border: 2px solid {self._accent}; "
                f"border-radius: 12px; padding: 20px; "
                f"color: {self._accent}; font-size: 14px; "
                f"background: #0D0D2A; min-height: 60px;"
            )

    def dragLeaveEvent(self, event):
        """Reset drop zone style on drag leave."""
        self._drop_zone.setStyleSheet(
            f"border: 2px dashed {self._accent}44; "
            f"border-radius: 12px; padding: 20px; "
            f"color: #8888AA; font-size: 14px; "
            f"background: #0D0D1A; min-height: 60px;"
        )

    def dropEvent(self, event: QDropEvent):
        """Process dropped files — extract .exe paths."""
        self._drop_zone.setStyleSheet(
            f"border: 2px dashed {self._accent}44; "
            f"border-radius: 12px; padding: 20px; "
            f"color: #8888AA; font-size: 14px; "
            f"background: #0D0D1A; min-height: 60px;"
        )

        paths = []
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            # Try resolving as .exe or .lnk shortcut
            resolved = _resolve_file_path(file_path)
            if resolved:
                paths.append(resolved)
            elif os.path.isdir(file_path):
                # Scan directory (non-recursive, first level only)
                for fname in os.listdir(file_path):
                    fpath = os.path.join(file_path, fname)
                    resolved = _resolve_file_path(fpath)
                    if resolved:
                        paths.append(resolved)

        self._add_exe_paths(paths)
        event.acceptProposedAction()

    # ── File Dialogs ───────────────────────────────────────────────────

    def _browse_exe_files(self):
        """Open file dialog to select multiple .exe files."""
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Game Executables", "",
            _get_file_filter()
        )
        if paths:
            # Resolve any .lnk shortcuts to their target exe
            resolved = []
            for p in paths:
                r = _resolve_file_path(p)
                if r:
                    resolved.append(r)
            if resolved:
                self._add_exe_paths(resolved)

    def _browse_folder(self):
        """Select a folder and scan it for .exe files."""
        folder = QFileDialog.getExistingDirectory(
            self, "Select Folder to Scan for Games"
        )
        if not folder:
            return

        paths = []
        for fname in os.listdir(folder):
            fpath = os.path.join(folder, fname)
            resolved = _resolve_file_path(fpath)
            if resolved:
                paths.append(resolved)

        self._add_exe_paths(paths)

    # ── Internal Helpers ───────────────────────────────────────────────

    def _add_exe_paths(self, paths: list[str]):
        """Add new .exe paths to the list, avoiding duplicates."""
        existing = {row.exe_path for row in self._rows if row.parent() is not None}

        for path in paths:
            if path not in existing:
                row = _GameRow(path, self._accent)
                self._list_layout.addWidget(row)
                self._rows.append(row)
                existing.add(path)

        self._update_count()

    def _clear_all(self):
        """Remove all rows."""
        for row in self._rows:
            row.setParent(None)
            row.deleteLater()
        self._rows.clear()
        self._update_count()

    def _update_count(self):
        """Update the count label."""
        # Filter out rows that have been removed
        self._rows = [r for r in self._rows if r.parent() is not None]
        count = len(self._rows)
        self._list_label.setText(
            f"{count} game{'s' if count != 1 else ''} selected"
        )

    def _on_add_all(self):
        """Validate and accept."""
        self._rows = [r for r in self._rows if r.parent() is not None]
        if not self._rows:
            self._drop_zone.setStyleSheet(
                f"border: 2px solid #CC3333; "
                f"border-radius: 12px; padding: 20px; "
                f"color: #CC3333; font-size: 14px; "
                f"background: #0D0D1A; min-height: 60px;"
            )
            return
        self.accept()

    def get_results(self) -> list[dict]:
        """Return list of game data dicts after acceptance."""
        self._rows = [r for r in self._rows if r.parent() is not None]
        results = []
        for row in self._rows:
            results.append({
                "name": row.game_name,
                "exe_path": row.exe_path,
                "cover_image_path": None,
            })
        return results
