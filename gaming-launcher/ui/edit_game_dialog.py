"""
Edit Game Dialog for Velox Gaming Launcher.

Allows editing game metadata (name, 1:1 square cover photo) and provides
the exclusive entry point to delete the game from the launcher.
"""

from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QFrame, QWidget, QSizePolicy
)
from PyQt6.QtCore import Qt, QPoint, QRectF
from PyQt6.QtGui import (
    QFont, QColor, QPixmap, QPainter, QPainterPath
)

from ui.game_card import _make_placeholder_pixmap


# ── Design tokens (mirroring main_window) ──────────────────────────────────────
BG_DARK    = "#080B14"
BG_SURF    = "#0F1623"
BG_RAISED  = "#161E2E"
ACCENT     = "#00C8FF"
ACCENT2    = "#7B2FFF"
TEXT       = "#E8F0FE"
TEXT_DIM   = "#6B7FA3"
BORDER     = "#1E2A42"
DANGER     = "#FF4444"
DANGER_BG  = "#2A1015"
# ──────────────────────────────────────────────────────────────────────────────


def make_rounded_pixmap(src_pixmap: QPixmap, size: int, radius: int = 10) -> QPixmap:
    """Scale a pixmap to a square with centered crop and rounded corners."""
    if src_pixmap.isNull():
        return src_pixmap

    # Square canvas
    dest = QPixmap(size, size)
    dest.fill(Qt.GlobalColor.transparent)

    # Scale maintaining aspect ratio by expanding to cover size x size
    scaled = src_pixmap.scaled(
        size, size,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )

    # Center crop offset
    x = (scaled.width() - size) // 2
    y = (scaled.height() - size) // 2

    painter = QPainter(dest)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, size, size), radius, radius)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, scaled, x, y, size, size)
    painter.end()

    return dest


class EditGameDialog(QDialog):
    """Modal dialog to edit game parameters or delete it."""

    PREVIEW_SIZE = 140

    def __init__(self, game_data: dict, parent=None):
        super().__init__(parent)
        self.game_id    = game_data["id"]
        self.orig_name  = game_data["name"]
        self.orig_cover = game_data.get("cover_image_path")
        self.exe_path   = game_data.get("exe_path", "")

        self.current_name  = self.orig_name
        self.current_cover = self.orig_cover
        self._is_deleted   = False

        self.setFixedWidth(460)
        self.setModal(True)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowSystemMenuHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        self._drag_pos: Optional[QPoint] = None

        self._setup_ui()
        self._apply_styles()
        self._update_preview()

    # ── Drag support ──────────────────────────────────────────────────────────
    def _on_title_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def _on_title_move(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    # ── UI Construction ───────────────────────────────────────────────────────
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Title bar ─────────────────────────────────────────────────────────
        title_bar = QWidget()
        title_bar.setObjectName("dlgTitleBar")
        title_bar.setFixedHeight(46)
        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(18, 0, 14, 0)

        title_lbl = QLabel("⚙  PARAMÈTRES DU JEU")
        title_lbl.setFont(QFont("Rajdhani", 12, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {ACCENT};")

        close_btn = QPushButton("✕")
        close_btn.setObjectName("dlgCloseBtn")
        close_btn.setFixedSize(28, 28)
        close_btn.clicked.connect(self.reject)

        tb_layout.addWidget(title_lbl)
        tb_layout.addStretch()
        tb_layout.addWidget(close_btn)

        title_bar.mousePressEvent = self._on_title_press
        title_bar.mouseMoveEvent  = self._on_title_move
        root.addWidget(title_bar)

        # ── Body ──────────────────────────────────────────────────────────────
        body = QWidget()
        body_l = QVBoxLayout(body)
        body_l.setContentsMargins(22, 18, 22, 18)
        body_l.setSpacing(18)

        # ── 1. Nom du jeu ─────────────────────────────────────────────────────
        name_group = QVBoxLayout()
        name_group.setSpacing(6)

        name_hdr = QLabel("Nom du jeu")
        name_hdr.setFont(QFont("Rajdhani", 10, QFont.Weight.Bold))
        name_hdr.setStyleSheet(f"color: {TEXT_DIM};")

        self.name_input = QLineEdit(self.current_name)
        self.name_input.setFont(QFont("Segoe UI", 10))
        self.name_input.setObjectName("formInput")
        self.name_input.setPlaceholderText("Entrez le nom du jeu...")
        self.name_input.textChanged.connect(self._on_name_changed)

        name_group.addWidget(name_hdr)
        name_group.addWidget(self.name_input)
        body_l.addLayout(name_group)

        # ── 2. Exécutable du jeu ──────────────────────────────────────────────
        exe_group = QVBoxLayout()
        exe_group.setSpacing(6)

        exe_hdr = QLabel("Exécutable du jeu (.exe, .lnk)")
        exe_hdr.setFont(QFont("Rajdhani", 10, QFont.Weight.Bold))
        exe_hdr.setStyleSheet(f"color: {TEXT_DIM};")

        exe_row = QHBoxLayout()
        exe_row.setSpacing(8)

        self.exe_input = QLineEdit(self.exe_path)
        self.exe_input.setFont(QFont("Segoe UI", 9))
        self.exe_input.setObjectName("formInput")
        self.exe_input.setPlaceholderText("Chemin vers l'exécutable (.exe)...")

        self.browse_exe_btn = QPushButton("📁  Parcourir...")
        self.browse_exe_btn.setObjectName("outlineBtn")
        self.browse_exe_btn.setFixedHeight(34)
        self.browse_exe_btn.clicked.connect(self._browse_exe)

        exe_row.addWidget(self.exe_input)
        exe_row.addWidget(self.browse_exe_btn)

        exe_group.addWidget(exe_hdr)
        exe_group.addLayout(exe_row)
        body_l.addLayout(exe_group)

        # ── 3. Pochette carrée (Format 1:1) ───────────────────────────────────
        cover_group = QVBoxLayout()
        cover_group.setSpacing(8)

        cover_hdr = QLabel("Photo de couverture (Format 1:1)")
        cover_hdr.setFont(QFont("Rajdhani", 10, QFont.Weight.Bold))
        cover_hdr.setStyleSheet(f"color: {TEXT_DIM};")
        cover_group.addWidget(cover_hdr)

        cover_row = QHBoxLayout()
        cover_row.setSpacing(16)

        # Preview square
        self.preview_lbl = QLabel()
        self.preview_lbl.setObjectName("coverPreview")
        self.preview_lbl.setFixedSize(self.PREVIEW_SIZE, self.PREVIEW_SIZE)
        self.preview_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cover_row.addWidget(self.preview_lbl)

        # Side controls
        side_col = QVBoxLayout()
        side_col.setSpacing(8)
        side_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.choose_img_btn = QPushButton("📁  Changer l'image...")
        self.choose_img_btn.setObjectName("outlineBtn")
        self.choose_img_btn.setFixedHeight(34)
        self.choose_img_btn.clicked.connect(self._browse_image)

        self.reset_img_btn = QPushButton("↺  Réinitialiser la photo")
        self.reset_img_btn.setObjectName("subtleBtn")
        self.reset_img_btn.setFixedHeight(30)
        self.reset_img_btn.clicked.connect(self._reset_image)

        hint_lbl = QLabel("Ratio carré 1:1 recommandé\nPNG, JPG, WEBP, BMP")
        hint_lbl.setFont(QFont("Segoe UI", 8))
        hint_lbl.setStyleSheet(f"color: {TEXT_DIM};")

        side_col.addWidget(self.choose_img_btn)
        side_col.addWidget(self.reset_img_btn)
        side_col.addWidget(hint_lbl)
        cover_row.addLayout(side_col)

        cover_group.addLayout(cover_row)
        body_l.addLayout(cover_group)

        # ── 4. Zone de danger (Suppression) ───────────────────────────────────
        danger_box = QFrame()
        danger_box.setObjectName("dangerBox")
        danger_l = QHBoxLayout(danger_box)
        danger_l.setContentsMargins(14, 12, 14, 12)
        danger_l.setSpacing(12)

        danger_text_col = QVBoxLayout()
        danger_text_col.setSpacing(2)

        danger_title = QLabel("Supprimer le jeu")
        danger_title.setFont(QFont("Rajdhani", 10, QFont.Weight.Bold))
        danger_title.setStyleSheet(f"color: {DANGER};")

        danger_desc = QLabel("Retire ce jeu de la bibliothèque Velox.")
        danger_desc.setFont(QFont("Segoe UI", 8))
        danger_desc.setStyleSheet(f"color: {TEXT_DIM};")

        danger_text_col.addWidget(danger_title)
        danger_text_col.addWidget(danger_desc)

        self.delete_btn = QPushButton("🗑  Supprimer")
        self.delete_btn.setObjectName("dangerBtn")
        self.delete_btn.setFixedHeight(32)
        self.delete_btn.clicked.connect(self._confirm_delete)

        danger_l.addLayout(danger_text_col)
        danger_l.addStretch()
        danger_l.addWidget(self.delete_btn)
        body_l.addWidget(danger_box)

        # ── 4. Bottom action buttons ──────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.cancel_btn = QPushButton("Annuler")
        self.cancel_btn.setObjectName("outlineBtn")
        self.cancel_btn.setFixedHeight(36)
        self.cancel_btn.clicked.connect(self.reject)

        self.save_btn = QPushButton("Enregistrer")
        self.save_btn.setObjectName("primaryBtn")
        self.save_btn.setFixedHeight(36)
        self.save_btn.clicked.connect(self._save)

        btn_row.addStretch()
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.save_btn)
        body_l.addLayout(btn_row)

        root.addWidget(body)

    # ── Preview update ────────────────────────────────────────────────────────
    def _update_preview(self):
        """Redraw preview image with 1:1 rounded square."""
        size = self.PREVIEW_SIZE

        if self.current_cover and Path(self.current_cover).exists():
            px = QPixmap(self.current_cover)
            if not px.isNull():
                rounded = make_rounded_pixmap(px, size, radius=8)
                self.preview_lbl.setPixmap(rounded)
                self.reset_img_btn.setEnabled(True)
                return

        # Fallback to initials placeholder
        words = self.current_name.strip().split()
        if len(words) >= 2:
            initials = (words[0][0] + words[1][0]).upper()
        elif len(words) == 1 and len(words[0]) >= 2:
            initials = words[0][:2].upper()
        else:
            initials = "??"

        placeholder = _make_placeholder_pixmap(size, size, initials, self.game_id)
        rounded = make_rounded_pixmap(placeholder, size, radius=8)
        self.preview_lbl.setPixmap(rounded)
        self.reset_img_btn.setEnabled(bool(self.current_cover))

    def _on_name_changed(self, text: str):
        self.current_name = text.strip() or self.orig_name
        if not self.current_cover:
            self._update_preview()

    def _browse_image(self):
        """Open file dialog to pick a new cover image."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choisir une image carrée",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp);;Tous les fichiers (*)"
        )
        if path:
            self.current_cover = path
            self._update_preview()

    def _browse_exe(self):
        """Open file dialog to pick a new game executable."""
        start_dir = ""
        current_text = self.exe_input.text().strip().strip('"\'')
        if current_text and Path(current_text).exists():
            start_dir = str(Path(current_text).parent)
        elif self.exe_path and Path(self.exe_path).exists():
            start_dir = str(Path(self.exe_path).parent)

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Sélectionner l'exécutable du jeu",
            start_dir,
            "Exécutables (*.exe *.lnk *.bat *.cmd);;Tous les fichiers (*)"
        )
        if path:
            self.exe_input.setText(path)

    def _reset_image(self):
        """Reset cover to None (will show initials placeholder)."""
        self.current_cover = None
        self._update_preview()

    def _confirm_delete(self):
        """Styled confirmation dialog before deletion."""
        dlg = QDialog(self)
        dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowType.FramelessWindowHint)
        dlg.setModal(True)
        dlg.setFixedWidth(360)
        dlg.setStyleSheet(f"""
            QDialog {{
                background-color: {BG_SURF};
                border: 1px solid {DANGER};
                border-radius: 12px;
            }}
            QLabel {{ color: {TEXT}; }}
        """)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(14)

        icon_lbl = QLabel("🗑  Supprimer le jeu ?")
        icon_lbl.setFont(QFont("Rajdhani", 13, QFont.Weight.Bold))
        icon_lbl.setStyleSheet(f"color: {DANGER};")
        layout.addWidget(icon_lbl)

        msg = QLabel(
            f"« {self.orig_name} » sera définitivement retiré du launcher.\n"
            f"Les fichiers de votre jeu ne seront pas affectés."
        )
        msg.setFont(QFont("Segoe UI", 9))
        msg.setWordWrap(True)
        msg.setStyleSheet(f"color: {TEXT_DIM};")
        layout.addWidget(msg)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        cancel_b = QPushButton("Annuler")
        cancel_b.setFixedHeight(34)
        cancel_b.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {BORDER};
                border-radius: 6px;
                color: {TEXT_DIM};
                font-size: 11px;
                padding: 0 14px;
            }}
            QPushButton:hover {{ color: {TEXT}; border-color: {TEXT_DIM}; }}
        """)
        cancel_b.clicked.connect(dlg.reject)

        confirm_b = QPushButton("🗑  Supprimer")
        confirm_b.setFixedHeight(34)
        confirm_b.setStyleSheet(f"""
            QPushButton {{
                background-color: {DANGER};
                border: none;
                border-radius: 6px;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 11px;
                padding: 0 16px;
            }}
            QPushButton:hover {{ background-color: #FF5555; }}
            QPushButton:pressed {{ background-color: #CC2222; }}
        """)
        confirm_b.clicked.connect(dlg.accept)

        btn_row.addWidget(cancel_b)
        btn_row.addStretch()
        btn_row.addWidget(confirm_b)
        layout.addLayout(btn_row)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._is_deleted = True
            self.accept()

    def _save(self):
        new_name = self.name_input.text().strip()
        if not new_name:
            self.name_input.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {BG_DARK};
                    border: 1px solid {DANGER};
                    border-radius: 6px;
                    padding: 6px 12px;
                    color: {TEXT};
                }}
            """)
            return
        self.current_name = new_name
        self.current_exe = self.exe_input.text().strip().strip('"\'')
        self.accept()

    # ── Public Result Accessors ───────────────────────────────────────────────
    def is_deleted(self) -> bool:
        return self._is_deleted

    def get_game_data(self) -> dict:
        return {
            "name": self.current_name,
            "cover_image_path": self.current_cover,
            "exe_path": getattr(self, "current_exe", self.exe_path),
        }

    # ── Styling ───────────────────────────────────────────────────────────────
    def _apply_styles(self):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {BG_SURF};
                border: 1px solid {BORDER};
                border-radius: 12px;
            }}

            #dlgTitleBar {{
                background-color: {BG_DARK};
                border-bottom: 1px solid {BORDER};
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
            }}

            #dlgCloseBtn {{
                background: transparent;
                border: none;
                color: {TEXT_DIM};
                font-size: 13px;
                border-radius: 5px;
            }}
            #dlgCloseBtn:hover {{
                background-color: #CC2222;
                color: #FFFFFF;
            }}

            #formInput {{
                background-color: {BG_DARK};
                border: 1px solid {BORDER};
                border-radius: 6px;
                padding: 6px 12px;
                color: {TEXT};
                font-size: 10px;
                selection-background-color: {ACCENT};
            }}
            #formInput:focus {{
                border: 1px solid {ACCENT};
            }}

            #coverPreview {{
                background-color: {BG_DARK};
                border: 1px solid {BORDER};
                border-radius: 8px;
            }}

            #dangerBox {{
                background-color: {DANGER_BG};
                border: 1px solid #4A1A22;
                border-radius: 8px;
            }}

            #dangerBtn {{
                background-color: transparent;
                border: 1px solid {DANGER};
                border-radius: 6px;
                color: {DANGER};
                font-weight: bold;
                font-size: 10px;
                padding: 0 12px;
            }}
            #dangerBtn:hover {{
                background-color: {DANGER};
                color: #FFFFFF;
            }}

            #outlineBtn {{
                background-color: transparent;
                border: 1px solid {BORDER};
                border-radius: 6px;
                color: {TEXT};
                font-size: 10px;
                padding: 0 14px;
            }}
            #outlineBtn:hover {{
                border-color: {ACCENT};
                color: {ACCENT};
            }}

            #subtleBtn {{
                background-color: transparent;
                border: none;
                color: {TEXT_DIM};
                font-size: 9px;
                text-align: left;
                padding: 0 4px;
            }}
            #subtleBtn:hover {{
                color: {TEXT};
            }}

            #primaryBtn {{
                background-color: {ACCENT};
                border: none;
                border-radius: 6px;
                color: #000000;
                font-weight: bold;
                font-size: 10px;
                padding: 0 18px;
            }}
            #primaryBtn:hover {{
                background-color: #33D4FF;
            }}
            #primaryBtn:pressed {{
                background-color: #0099CC;
            }}
        """)
