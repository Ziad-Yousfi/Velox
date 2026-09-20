"""
Add Game Dialog for Velox Gaming Launcher.

Supports two modes:
- Scan Folder(s): select one or more folders, auto-detect the main .exe in each,
  preview detected games with checkboxes, then bulk-add.
- Manual: classic name + .exe + cover selection.
"""

import os
import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QTabWidget, QWidget,
    QListWidget, QListWidgetItem, QCheckBox, QScrollArea,
    QFrame, QSizePolicy, QAbstractItemView
)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor


# ---------------------------------------------------------------------------
# Patterns to ignore when looking for a game executable
# ---------------------------------------------------------------------------
_IGNORE_PATTERNS = [
    "unins", "uninstall", "setup", "install", "crash", "report",
    "helper", "launcher_helper", "cefsubprocess", "cef_subprocess",
    "dxsetup", "vcredist", "vc_redist", "unarc", "7z", "7zg",
    "dotnet", "directx", "physxcooking", "uplayinstaller",
    "easyanticheat", "battleye", "be_service", "steamerrorreporter",
    "steamwebhelper", "gameoverlayui", "winstore.app",
]


def _is_likely_game_exe(exe_path: Path) -> bool:
    """Return True if the exe is likely the main game executable."""
    name = exe_path.stem.lower()
    for pat in _IGNORE_PATTERNS:
        if pat in name:
            return False
    return True


def _find_best_exe(folder: Path) -> Path | None:
    """
    Scan *folder* (non-recursive first, then one level deep) for .exe files,
    filter noise, and return the most likely game executable.

    Heuristic order:
      1. Only one candidate → return it.
      2. Largest file (games are typically the biggest exe).
      3. File whose name is closest to the folder name.
    """
    folder = Path(folder)
    if not folder.is_dir():
        return None

    # Collect candidates (root level first, then one sub-level)
    candidates: list[Path] = []
    for p in folder.iterdir():
        if p.suffix.lower() == ".exe" and _is_likely_game_exe(p):
            candidates.append(p)

    if not candidates:
        # Go one level deeper
        for sub in folder.iterdir():
            if sub.is_dir():
                for p in sub.iterdir():
                    if p.suffix.lower() == ".exe" and _is_likely_game_exe(p):
                        candidates.append(p)

    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    # Prefer the file whose stem matches the folder name (case-insensitive)
    folder_name = folder.name.lower().replace(" ", "").replace("-", "").replace("_", "")
    for c in candidates:
        stem = c.stem.lower().replace(" ", "").replace("-", "").replace("_", "")
        if stem == folder_name or folder_name in stem or stem in folder_name:
            return c

    # Fall back to largest file
    return max(candidates, key=lambda p: p.stat().st_size)


def _pretty_name(folder: Path) -> str:
    """Derive a pretty game name from a folder path."""
    name = folder.name
    # Remove common suffixes like _win64, -release, etc.
    for suffix in [
        "_win64", "_win32", "-win64", "-win32",
        "_release", "-release", "_game", "-game",
    ]:
        if name.lower().endswith(suffix):
            name = name[: -len(suffix)]
    return name.replace("_", " ").replace("-", " ").title()


# ---------------------------------------------------------------------------
# Detected-game row widget (used in the scan tab)
# ---------------------------------------------------------------------------
class DetectedGameRow(QFrame):
    """A row showing a detected game with a checkbox, name and exe path."""

    ACCENT = "#00C8FF"
    BG = "#0F1623"
    BG_HOVER = "#161E2E"

    def __init__(self, game_name: str, exe_path: str, parent=None):
        super().__init__(parent)
        self.setObjectName("detectedRow")
        self._exe_path = exe_path
        self._name = game_name

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        # Checkbox
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(True)
        self.checkbox.setFixedSize(20, 20)
        layout.addWidget(self.checkbox)

        # Icon / label
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        self.name_label = QLabel(game_name)
        self.name_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.name_label.setStyleSheet(f"color: #E8F0FE;")

        self.path_label = QLabel(exe_path)
        self.path_label.setFont(QFont("Segoe UI", 8))
        self.path_label.setStyleSheet("color: #6B7FA3;")
        self.path_label.setWordWrap(False)
        self.path_label.setMaximumWidth(480)

        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.path_label)
        layout.addLayout(info_layout)
        layout.addStretch()

        # Editable name button
        edit_btn = QPushButton("✏")
        edit_btn.setFixedSize(28, 28)
        edit_btn.setToolTip("Edit name")
        edit_btn.setObjectName("editBtn")
        edit_btn.clicked.connect(self._toggle_edit)
        layout.addWidget(edit_btn)

        # Name editor (hidden initially)
        self.name_editor = QLineEdit(game_name)
        self.name_editor.setFixedHeight(28)
        self.name_editor.setMinimumWidth(160)
        self.name_editor.setMaximumWidth(200)
        self.name_editor.hide()
        self.name_editor.returnPressed.connect(self._apply_edit)
        layout.addWidget(self.name_editor)

        self._apply_base_style()

    def _apply_base_style(self):
        self.setStyleSheet(f"""
            #detectedRow {{
                background-color: {self.BG};
                border: 1px solid #1E2A42;
                border-radius: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {self.ACCENT};
                border-radius: 4px;
                background-color: transparent;
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.ACCENT};
            }}
            #editBtn {{
                background-color: transparent;
                border: 1px solid #1E2A42;
                border-radius: 5px;
                color: #6B7FA3;
                font-size: 12px;
            }}
            #editBtn:hover {{
                background-color: #1E2A42;
                color: {self.ACCENT};
            }}
        """)

    def _toggle_edit(self):
        if self.name_editor.isHidden():
            self.name_editor.setText(self.name_label.text())
            self.name_editor.show()
            self.name_editor.setFocus()
            self.name_label.hide()
        else:
            self._apply_edit()

    def _apply_edit(self):
        new_name = self.name_editor.text().strip()
        if new_name:
            self._name = new_name
            self.name_label.setText(new_name)
        self.name_editor.hide()
        self.name_label.show()

    @property
    def is_selected(self) -> bool:
        return self.checkbox.isChecked()

    @property
    def game_name(self) -> str:
        return self._name

    @property
    def exe_path(self) -> str:
        return self._exe_path


# ---------------------------------------------------------------------------
# Native Windows Multi-Folder Picker
# ---------------------------------------------------------------------------
def pick_multiple_folders(parent_hwnd: int = 0, title: str = "Sélectionner des dossiers") -> list[str]:
    """
    Open the native Windows FileOpenDialog configured for multi-folder selection.
    Uses COM IFileOpenDialog with FOS_PICKFOLDERS | FOS_ALLOWMULTISELECT.
    Allows user to select multiple folders natively using standard Windows Explorer
    dialog (Ctrl+Click, Shift+Click, or mouse drag/lasso).
    """
    if sys.platform != "win32":
        return []

    try:
        import ctypes
        from ctypes import wintypes, c_void_p, POINTER, byref, HRESULT, WINFUNCTYPE, Structure

        ole32 = ctypes.windll.ole32
        ole32.CoTaskMemFree.argtypes = [c_void_p]

        class GUID(Structure):
            _fields_ = [
                ("Data1", wintypes.DWORD),
                ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD),
                ("Data4", wintypes.BYTE * 8)
            ]
            def __init__(self, l, w1, w2, b1, b2, b3, b4, b5, b6, b7, b8):
                super().__init__()
                self.Data1 = l
                self.Data2 = w1
                self.Data3 = w2
                self.Data4 = (wintypes.BYTE * 8)(b1, b2, b3, b4, b5, b6, b7, b8)

        CLSID_FileOpenDialog = GUID(0xDC1C5A9C, 0xE88A, 0x4DDE, 0xA5, 0xA1, 0x60, 0xF8, 0x2A, 0x20, 0xAE, 0xF7)
        IID_IFileOpenDialog = GUID(0xd57c7288, 0xd4ad, 0x4768, 0xbe, 0x02, 0x9d, 0x96, 0x95, 0x32, 0xd9, 0x60)

        proto_Release = WINFUNCTYPE(wintypes.ULONG, c_void_p)
        proto_Show = WINFUNCTYPE(HRESULT, c_void_p, wintypes.HWND)
        proto_SetOptions = WINFUNCTYPE(HRESULT, c_void_p, wintypes.DWORD)
        proto_GetOptions = WINFUNCTYPE(HRESULT, c_void_p, POINTER(wintypes.DWORD))
        proto_SetTitle = WINFUNCTYPE(HRESULT, c_void_p, wintypes.LPCWSTR)
        proto_GetResults = WINFUNCTYPE(HRESULT, c_void_p, POINTER(c_void_p))

        proto_Array_GetCount = WINFUNCTYPE(HRESULT, c_void_p, POINTER(wintypes.DWORD))
        proto_Array_GetItemAt = WINFUNCTYPE(HRESULT, c_void_p, wintypes.DWORD, POINTER(c_void_p))
        proto_Item_GetDisplayName = WINFUNCTYPE(HRESULT, c_void_p, wintypes.DWORD, POINTER(c_void_p))

        co_init_hr = ole32.CoInitialize(None)
        p_dialog = c_void_p()
        hr = ole32.CoCreateInstance(
            byref(CLSID_FileOpenDialog),
            None,
            1,  # CLSCTX_INPROC_SERVER
            byref(IID_IFileOpenDialog),
            byref(p_dialog)
        )
        if hr != 0 or not p_dialog:
            if co_init_hr in (0, 1):
                ole32.CoUninitialize()
            return []

        try:
            vtable = ctypes.cast(p_dialog, POINTER(POINTER(c_void_p))).contents

            release_dialog = proto_Release(vtable[2])
            show_dialog = proto_Show(vtable[3])
            set_options = proto_SetOptions(vtable[9])
            get_options = proto_GetOptions(vtable[10])
            set_title = proto_SetTitle(vtable[17])
            get_results = proto_GetResults(vtable[27])

            options = wintypes.DWORD()
            get_options(p_dialog, byref(options))

            FOS_PICKFOLDERS = 0x00000020
            FOS_ALLOWMULTISELECT = 0x00000200
            FOS_FORCEFILESYSTEM = 0x00000040

            set_options(p_dialog, options.value | FOS_PICKFOLDERS | FOS_ALLOWMULTISELECT | FOS_FORCEFILESYSTEM)

            if title:
                set_title(p_dialog, title)

            hr = show_dialog(p_dialog, wintypes.HWND(parent_hwnd))
            if hr != 0:  # User cancelled or closed dialog
                return []

            p_array = c_void_p()
            hr = get_results(p_dialog, byref(p_array))
            if hr != 0 or not p_array:
                return []

            try:
                arr_vtable = ctypes.cast(p_array, POINTER(POINTER(c_void_p))).contents
                release_array = proto_Release(arr_vtable[2])
                get_count = proto_Array_GetCount(arr_vtable[7])
                get_item_at = proto_Array_GetItemAt(arr_vtable[8])

                count = wintypes.DWORD()
                get_count(p_array, byref(count))

                results = []
                SIGDN_FILESYSPATH = 0x80058000

                for i in range(count.value):
                    p_item = c_void_p()
                    if get_item_at(p_array, i, byref(p_item)) == 0 and p_item:
                        try:
                            item_vtable = ctypes.cast(p_item, POINTER(POINTER(c_void_p))).contents
                            release_item = proto_Release(item_vtable[2])
                            get_display_name = proto_Item_GetDisplayName(item_vtable[5])

                            p_str = c_void_p()
                            if get_display_name(p_item, SIGDN_FILESYSPATH, byref(p_str)) == 0 and p_str:
                                path_str = ctypes.wstring_at(p_str)
                                ole32.CoTaskMemFree(p_str)
                                if path_str and os.path.exists(path_str):
                                    results.append(os.path.normpath(path_str))
                        finally:
                            release_item(p_item)

                return results
            finally:
                release_array(p_array)
        finally:
            release_dialog(p_dialog)
            if co_init_hr in (0, 1):
                ole32.CoUninitialize()

    except Exception as e:
        print(f"[pick_multiple_folders] Native Windows dialog error: {e}")
        return []


# ---------------------------------------------------------------------------
# Main Dialog
# ---------------------------------------------------------------------------
class AddGameDialog(QDialog):
    """Dialog for adding games — supports folder scan (bulk) or manual entry."""

    ACCENT = "#00C8FF"
    ACCENT2 = "#7B2FFF"
    BG = "#0F1623"
    BG_DARK = "#080B14"
    INPUT_BG = "#0A0E1A"
    BORDER = "#1E2A42"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Games")
        self.setMinimumSize(560, 480)
        self.setModal(True)

        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowSystemMenuHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        # State
        self._scanned_folders: list[str] = []       # folders added by user
        self._detected_rows: list[DetectedGameRow] = []  # row widgets
        self._manual_exe_path = ""
        self._manual_cover_path = None

        # drag support for frameless
        self._drag_pos = None

        self._setup_ui()
        self._apply_styles()

    # ------------------------------------------------------------------
    # UI Setup
    # ------------------------------------------------------------------
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Title bar ──────────────────────────────────────────────────
        title_bar = QFrame()
        title_bar.setObjectName("dlgTitleBar")
        title_bar.setFixedHeight(44)
        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(16, 0, 10, 0)

        logo = QLabel("⚡ ADD GAMES")
        logo.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        logo.setStyleSheet(f"color: {self.ACCENT};")

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setObjectName("dlgCloseBtn")
        close_btn.clicked.connect(self.reject)

        tb_layout.addWidget(logo)
        tb_layout.addStretch()
        tb_layout.addWidget(close_btn)

        title_bar.mousePressEvent = self._on_title_press
        title_bar.mouseMoveEvent = self._on_title_move

        root.addWidget(title_bar)

        # ── Tab widget ─────────────────────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setObjectName("dlgTabs")

        # Tab 1: Scan folders
        scan_tab = QWidget()
        self._build_scan_tab(scan_tab)
        self.tabs.addTab(scan_tab, "📂  Scan Dossier(s)")

        # Tab 2: Manual
        manual_tab = QWidget()
        self._build_manual_tab(manual_tab)
        self.tabs.addTab(manual_tab, "⚙  Manuel (.exe)")

        wrapper = QWidget()
        wrapper.setObjectName("tabsWrapper")
        wl = QVBoxLayout(wrapper)
        wl.setContentsMargins(16, 12, 16, 16)
        wl.addWidget(self.tabs)
        root.addWidget(wrapper)

    # ── Scan tab ───────────────────────────────────────────────────────
    def _build_scan_tab(self, parent: QWidget):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(10)

        # Folder list header
        hdr = QHBoxLayout()
        lbl = QLabel("Dossiers à scanner :")
        lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl.setStyleSheet("color: #E8F0FE;")

        add_folder_btn = QPushButton("+ Ajouter dossier(s)")
        add_folder_btn.setObjectName("accentBtn")
        add_folder_btn.setFixedHeight(30)
        add_folder_btn.clicked.connect(self._add_folder)

        clear_btn = QPushButton("Tout effacer")
        clear_btn.setObjectName("outlineBtn")
        clear_btn.setFixedHeight(30)
        clear_btn.clicked.connect(self._clear_folders)

        hdr.addWidget(lbl)
        hdr.addStretch()
        hdr.addWidget(add_folder_btn)
        hdr.addWidget(clear_btn)
        layout.addLayout(hdr)

        # Folder list
        self.folder_list = QListWidget()
        self.folder_list.setFixedHeight(90)
        self.folder_list.setObjectName("folderList")
        self.folder_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        layout.addWidget(self.folder_list)

        # Delete selected folder
        del_hdr = QHBoxLayout()
        del_hdr.addStretch()
        remove_folder_btn = QPushButton("✕  Retirer sélectionné")
        remove_folder_btn.setObjectName("dangerBtn")
        remove_folder_btn.setFixedHeight(26)
        remove_folder_btn.clicked.connect(self._remove_selected_folder)
        del_hdr.addWidget(remove_folder_btn)
        layout.addLayout(del_hdr)

        # Scan button
        self.scan_btn = QPushButton("🔍  Scanner les dossiers")
        self.scan_btn.setObjectName("scanBtn")
        self.scan_btn.setFixedHeight(38)
        self.scan_btn.clicked.connect(self._scan_folders)
        layout.addWidget(self.scan_btn)

        # Status label
        self.scan_status = QLabel("")
        self.scan_status.setFont(QFont("Segoe UI", 9))
        self.scan_status.setStyleSheet("color: #6B7FA3;")
        self.scan_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.scan_status)

        # Detected games area
        detected_lbl = QLabel("Jeux détectés :")
        detected_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        detected_lbl.setStyleSheet("color: #E8F0FE;")
        layout.addWidget(detected_lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("detectedScroll")
        scroll.setMinimumHeight(120)

        self.detected_container = QWidget()
        self.detected_layout = QVBoxLayout(self.detected_container)
        self.detected_layout.setSpacing(6)
        self.detected_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.detected_container)
        layout.addWidget(scroll)

        # Bottom: select all + add
        bottom = QHBoxLayout()
        sel_all_btn = QPushButton("☑  Tout sélectionner")
        sel_all_btn.setObjectName("outlineBtn")
        sel_all_btn.setFixedHeight(34)
        sel_all_btn.clicked.connect(self._select_all)

        desel_btn = QPushButton("☐  Tout désel.")
        desel_btn.setObjectName("outlineBtn")
        desel_btn.setFixedHeight(34)
        desel_btn.clicked.connect(self._deselect_all)

        self.add_selected_btn = QPushButton("✔  Ajouter sélectionnés")
        self.add_selected_btn.setObjectName("accentBtn")
        self.add_selected_btn.setFixedHeight(34)
        self.add_selected_btn.clicked.connect(self._accept_scan)

        bottom.addWidget(sel_all_btn)
        bottom.addWidget(desel_btn)
        bottom.addStretch()
        bottom.addWidget(self.add_selected_btn)
        layout.addLayout(bottom)

    # ── Manual tab ─────────────────────────────────────────────────────
    def _build_manual_tab(self, parent: QWidget):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(14)

        # Game name
        name_lbl = QLabel("Nom du jeu :")
        name_lbl.setFont(QFont("Segoe UI", 10))
        name_lbl.setStyleSheet("color: #E8F0FE;")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Entrez le nom du jeu...")
        self.name_input.setFixedHeight(36)
        layout.addWidget(name_lbl)
        layout.addWidget(self.name_input)

        # Executable
        exe_lbl = QLabel("Exécutable (.exe) :")
        exe_lbl.setFont(QFont("Segoe UI", 10))
        exe_lbl.setStyleSheet("color: #E8F0FE;")
        exe_row = QHBoxLayout()
        self.exe_input = QLineEdit()
        self.exe_input.setPlaceholderText("Sélectionnez l'exécutable du jeu...")
        self.exe_input.setReadOnly(True)
        self.exe_input.setFixedHeight(36)
        browse_exe_btn = QPushButton("Parcourir…")
        browse_exe_btn.setObjectName("outlineBtn")
        browse_exe_btn.setFixedHeight(36)
        browse_exe_btn.clicked.connect(self._browse_exe)
        exe_row.addWidget(self.exe_input)
        exe_row.addWidget(browse_exe_btn)
        layout.addWidget(exe_lbl)
        layout.addLayout(exe_row)

        # Cover image
        cover_lbl = QLabel("Image de couverture (optionnel) :")
        cover_lbl.setFont(QFont("Segoe UI", 10))
        cover_lbl.setStyleSheet("color: #E8F0FE;")
        cover_row = QHBoxLayout()
        self.cover_input = QLineEdit()
        self.cover_input.setPlaceholderText("Sélectionnez une image...")
        self.cover_input.setReadOnly(True)
        self.cover_input.setFixedHeight(36)
        browse_cover_btn = QPushButton("Parcourir…")
        browse_cover_btn.setObjectName("outlineBtn")
        browse_cover_btn.setFixedHeight(36)
        browse_cover_btn.clicked.connect(self._browse_cover)
        cover_row.addWidget(self.cover_input)
        cover_row.addWidget(browse_cover_btn)
        layout.addWidget(cover_lbl)
        layout.addLayout(cover_row)

        layout.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("Annuler")
        cancel_btn.setObjectName("outlineBtn")
        cancel_btn.setFixedHeight(38)
        cancel_btn.clicked.connect(self.reject)

        add_btn = QPushButton("✔  Ajouter")
        add_btn.setObjectName("accentBtn")
        add_btn.setFixedHeight(38)
        add_btn.clicked.connect(self._accept_manual)

        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(add_btn)
        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Folder scan logic
    # ------------------------------------------------------------------
    def _add_folder(self):
        """Open native Windows dialog to select one or multiple folders at once."""
        parent_hwnd = int(self.winId()) if sys.platform == "win32" else 0
        folders = pick_multiple_folders(parent_hwnd, "Sélectionner des dossiers de jeux")

        # Fallback for non-Windows platforms
        if not folders and sys.platform != "win32":
            folder = QFileDialog.getExistingDirectory(self, "Sélectionner un dossier de jeux")
            if folder:
                folders = [folder]

        if not folders:
            return

        added_count = 0
        for folder in folders:
            if folder not in self._scanned_folders:
                self._scanned_folders.append(folder)
                item = QListWidgetItem(folder)
                item.setForeground(QColor("#E8F0FE"))
                self.folder_list.addItem(item)
                added_count += 1

        if added_count > 0:
            n = len(self._scanned_folders)
            self.scan_status.setText(
                f"{n} dossier{'s' if n > 1 else ''} prêt{'s' if n > 1 else ''} à être analysé{'s' if n > 1 else ''}."
            )

    def _remove_selected_folder(self):
        selected = self.folder_list.selectedItems()
        for item in selected:
            folder = item.text()
            if folder in self._scanned_folders:
                self._scanned_folders.remove(folder)
            row = self.folder_list.row(item)
            self.folder_list.takeItem(row)

    def _clear_folders(self):
        self._scanned_folders.clear()
        self.folder_list.clear()
        self._clear_detected()

    def _clear_detected(self):
        self._detected_rows.clear()
        while self.detected_layout.count():
            item = self.detected_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _scan_folders(self):
        if not self._scanned_folders:
            self.scan_status.setText("⚠  Aucun dossier sélectionné.")
            return

        self._clear_detected()
        found = 0

        for folder_str in self._scanned_folders:
            folder = Path(folder_str)
            exe = _find_best_exe(folder)

            if exe:
                name = _pretty_name(folder)
                row = DetectedGameRow(name, str(exe))
                self._detected_rows.append(row)
                self.detected_layout.addWidget(row)
                found += 1
            else:
                # Nothing found — show a disabled placeholder row
                placeholder = QLabel(f"⚠  Aucun .exe trouvé dans : {folder.name}")
                placeholder.setStyleSheet("color: #FF6B6B; padding: 6px 12px;")
                self.detected_layout.addWidget(placeholder)

        self.scan_status.setText(
            f"✔  {found} jeu(x) détecté(s) sur {len(self._scanned_folders)} dossier(s)."
            if found else "Aucun jeu détecté."
        )

    def _select_all(self):
        for row in self._detected_rows:
            row.checkbox.setChecked(True)

    def _deselect_all(self):
        for row in self._detected_rows:
            row.checkbox.setChecked(False)

    def _accept_scan(self):
        selected = [r for r in self._detected_rows if r.is_selected]
        if not selected:
            self.scan_status.setText("⚠  Sélectionnez au moins un jeu.")
            return
        # Store results and accept
        self._scan_results = selected
        self._mode = "scan"
        self.accept()

    # ------------------------------------------------------------------
    # Manual mode logic
    # ------------------------------------------------------------------
    def _browse_exe(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Sélectionner l'exécutable", "",
            "Executables (*.exe);;Tous les fichiers (*)"
        )
        if path:
            self._manual_exe_path = path
            self.exe_input.setText(path)
            if not self.name_input.text().strip():
                self.name_input.setText(_pretty_name(Path(path).parent))

    def _browse_cover(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Sélectionner une image de couverture", "",
            "Images (*.png *.jpg *.jpeg *.bmp);;Tous les fichiers (*)"
        )
        if path:
            self._manual_cover_path = path
            self.cover_input.setText(path)

    def _accept_manual(self):
        name = self.name_input.text().strip()
        if not name:
            self.name_input.setStyleSheet(
                "background-color: #2A1020; border: 1px solid #FF4444;"
                "border-radius:5px; padding:5px 10px; color:#FFFFFF;"
            )
            return
        if not self._manual_exe_path:
            self.exe_input.setStyleSheet(
                "background-color: #2A1020; border: 1px solid #FF4444;"
                "border-radius:5px; padding:5px 10px; color:#FFFFFF;"
            )
            return
        self._mode = "manual"
        self.accept()

    # ------------------------------------------------------------------
    # Public API — called by main_window after accept()
    # ------------------------------------------------------------------
    def get_mode(self) -> str:
        """Returns 'scan' or 'manual'."""
        return getattr(self, "_mode", "manual")

    def get_game_data(self) -> dict:
        """For manual mode — returns single game dict."""
        return {
            "name": self.name_input.text().strip(),
            "exe_path": self._manual_exe_path,
            "cover_image_path": self._manual_cover_path,
        }

    def get_scan_results(self) -> list[dict]:
        """For scan mode — returns list of game dicts."""
        results = getattr(self, "_scan_results", [])
        return [
            {"name": r.game_name, "exe_path": r.exe_path, "cover_image_path": None}
            for r in results
        ]

    # ------------------------------------------------------------------
    # Drag / frameless support
    # ------------------------------------------------------------------
    def _on_title_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def _on_title_move(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    # ------------------------------------------------------------------
    # Styles
    # ------------------------------------------------------------------
    def _apply_styles(self):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.BG};
                border: 1px solid {self.BORDER};
                border-radius: 12px;
            }}

            #dlgTitleBar {{
                background-color: {self.BG_DARK};
                border-bottom: 1px solid {self.BORDER};
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
            }}

            #dlgCloseBtn {{
                background-color: transparent;
                border: none;
                color: #6B7FA3;
                font-size: 13px;
                border-radius: 5px;
            }}
            #dlgCloseBtn:hover {{
                background-color: #CC2222;
                color: #FFFFFF;
            }}

            #tabsWrapper {{
                background-color: {self.BG};
            }}

            QTabWidget::pane {{
                border: 1px solid {self.BORDER};
                border-radius: 8px;
                background-color: {self.BG_DARK};
                padding: 4px;
            }}

            QTabBar::tab {{
                background-color: transparent;
                color: #6B7FA3;
                padding: 8px 18px;
                font-size: 10px;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                margin-right: 4px;
            }}
            QTabBar::tab:selected {{
                background-color: {self.ACCENT};
                color: #000000;
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {self.BORDER};
                color: #E8F0FE;
            }}

            QLabel {{ color: #E8F0FE; }}

            QLineEdit {{
                background-color: {self.INPUT_BG};
                border: 1px solid {self.BORDER};
                border-radius: 6px;
                padding: 5px 10px;
                color: #E8F0FE;
                font-size: 10px;
                selection-background-color: {self.ACCENT};
            }}
            QLineEdit:focus {{
                border: 1px solid {self.ACCENT};
            }}
            QLineEdit[readOnly="true"] {{
                color: #6B7FA3;
            }}

            #folderList {{
                background-color: {self.INPUT_BG};
                border: 1px solid {self.BORDER};
                border-radius: 6px;
                color: #E8F0FE;
                font-size: 9px;
            }}
            #folderList::item:selected {{
                background-color: {self.BORDER};
            }}

            #detectedScroll {{
                border: 1px solid {self.BORDER};
                border-radius: 8px;
                background-color: {self.BG_DARK};
            }}
            #detectedScroll QScrollBar:vertical {{
                background: transparent;
                width: 6px;
            }}
            #detectedScroll QScrollBar::handle:vertical {{
                background: {self.BORDER};
                border-radius: 3px;
                min-height: 20px;
            }}
            #detectedScroll QScrollBar::handle:vertical:hover {{
                background: {self.ACCENT};
            }}
            #detectedScroll QScrollBar::add-line:vertical,
            #detectedScroll QScrollBar::sub-line:vertical {{
                height: 0;
            }}

            /* Buttons */
            #accentBtn {{
                background-color: {self.ACCENT};
                color: #000000;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 10px;
                padding: 0 14px;
            }}
            #accentBtn:hover {{
                background-color: #33D4FF;
            }}
            #accentBtn:pressed {{
                background-color: #0099CC;
            }}

            #outlineBtn {{
                background-color: transparent;
                border: 1px solid {self.BORDER};
                border-radius: 6px;
                color: #6B7FA3;
                font-size: 10px;
                padding: 0 12px;
            }}
            #outlineBtn:hover {{
                border-color: {self.ACCENT};
                color: {self.ACCENT};
            }}

            #dangerBtn {{
                background-color: transparent;
                border: 1px solid #3A1A1A;
                border-radius: 5px;
                color: #FF6B6B;
                font-size: 9px;
                padding: 0 10px;
            }}
            #dangerBtn:hover {{
                background-color: #3A1A1A;
            }}

            #scanBtn {{
                background-color: transparent;
                border: 2px solid {self.ACCENT};
                border-radius: 8px;
                color: {self.ACCENT};
                font-weight: bold;
                font-size: 11px;
                padding: 0 20px;
            }}
            #scanBtn:hover {{
                background-color: {self.ACCENT};
                color: #000000;
            }}
            #scanBtn:pressed {{
                background-color: #0099CC;
                border-color: #0099CC;
            }}
        """)
