"""
Add Game dialog for the Gaming Launcher.
Lets the user:
  1. Pick a .exe file via native file dialog
  2. Set a custom display name
  3. Optionally select a cover image
"""

import os
import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QFrame
)
from PyQt6.QtGui import QPixmap, QPainter, QColor, QLinearGradient
from PyQt6.QtCore import Qt


class AddGameDialog(QDialog):
    """Modal dialog for adding a new game to the launcher."""

    def __init__(self, accent: str = "#00D4FF", parent=None):
        super().__init__(parent)
        self._accent = accent
        self._exe_path = ""
        self._cover_path = ""

        self.setWindowTitle("Add Game")
        self.setFixedSize(460, 340)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Title
        title = QLabel("ADD NEW GAME")
        title.setStyleSheet(
            f"font-size: 20px; font-weight: 700; color: {self._accent};"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: #222233;")
        sep.setFixedHeight(1)
        layout.addWidget(sep)

        # ── Executable path ────────────────────────────────────────────
        exe_label = QLabel("Executable (.exe)")
        exe_label.setStyleSheet("font-weight: 600; font-size: 13px;")
        layout.addWidget(exe_label)

        exe_row = QHBoxLayout()
        self._exe_input = QLineEdit()
        self._exe_input.setPlaceholderText("Select the game executable...")
        self._exe_input.setReadOnly(True)
        exe_row.addWidget(self._exe_input)

        browse_btn = QPushButton("Browse")
        browse_btn.setFixedWidth(80)
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.clicked.connect(self._browse_exe)
        exe_row.addWidget(browse_btn)
        layout.addLayout(exe_row)

        # ── Game name ──────────────────────────────────────────────────
        name_label = QLabel("Display Name")
        name_label.setStyleSheet("font-weight: 600; font-size: 13px;")
        layout.addWidget(name_label)

        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("e.g. Elden Ring")
        layout.addWidget(self._name_input)

        # ── Cover image ────────────────────────────────────────────────
        cover_label = QLabel("Cover Image (optional)")
        cover_label.setStyleSheet("font-weight: 600; font-size: 13px;")
        layout.addWidget(cover_label)

        cover_row = QHBoxLayout()
        self._cover_input = QLineEdit()
        self._cover_input.setPlaceholderText("No image selected")
        self._cover_input.setReadOnly(True)
        cover_row.addWidget(self._cover_input)

        cover_btn = QPushButton("Browse")
        cover_btn.setFixedWidth(80)
        cover_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cover_btn.clicked.connect(self._browse_cover)
        cover_row.addWidget(cover_btn)
        layout.addLayout(cover_row)

        layout.addStretch()

        # ── Action buttons ─────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(36)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        add_btn = QPushButton("Add Game")
        add_btn.setObjectName("accentBtn")
        add_btn.setFixedHeight(36)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self._on_add)
        btn_row.addWidget(add_btn)

        layout.addLayout(btn_row)

    # ── File Dialogs ───────────────────────────────────────────────────

    def _browse_exe(self):
        # Platform-appropriate file filter
        if sys.platform == "win32":
            file_filter = "Executables (*.exe);;All Files (*)"
        elif sys.platform == "darwin":
            file_filter = "Applications (*.app);;All Files (*)"
        else:
            file_filter = "All Files (*)"

        path, _ = QFileDialog.getOpenFileName(
            self, "Select Game Executable", "",
            file_filter
        )
        if path:
            self._exe_path = path
            self._exe_input.setText(path)

            # Auto-fill name from filename if empty
            if not self._name_input.text().strip():
                basename = os.path.splitext(os.path.basename(path))[0]
                # Clean up common suffixes
                for suffix in ["-Win64-Shipping", "_x64", "_x86", "-Win64"]:
                    basename = basename.replace(suffix, "")
                self._name_input.setText(basename.replace("_", " ").title())

    def _browse_cover(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Cover Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp);;All Files (*)"
        )
        if path:
            self._cover_path = path
            self._cover_input.setText(os.path.basename(path))

    # ── Validation & Result ────────────────────────────────────────────

    def _on_add(self):
        if not self._exe_path:
            self._exe_input.setStyleSheet(
                "border: 1px solid #CC3333; border-radius: 6px;"
            )
            return
        if not self._name_input.text().strip():
            self._name_input.setStyleSheet(
                "border: 1px solid #CC3333; border-radius: 6px;"
            )
            return
        self.accept()

    def get_result(self) -> dict:
        """Return the dialog data after acceptance."""
        return {
            "name": self._name_input.text().strip(),
            "exe_path": self._exe_path,
            "cover_image_path": self._cover_path or None,
        }
