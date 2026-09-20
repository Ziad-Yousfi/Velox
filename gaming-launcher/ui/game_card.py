"""
Game Card Widget for Velox Gaming Launcher.

A premium card widget displaying game information with:
- Cover image or stylized initial placeholder (drawn via QPainter)
- Game name, playtime, last-played badge
- Launch & Stats buttons
- Glow hover effects via QGraphicsDropShadowEffect
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGraphicsDropShadowEffect, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRectF
from PyQt6.QtGui import (
    QFont, QPixmap, QPainter, QColor, QLinearGradient,
    QBrush, QPen, QFontMetrics, QPainterPath
)

# ── Design tokens (mirror main_window) ────────────────────────────────────────
BG_CARD   = "#0F1623"
BG_HOVER  = "#161E2E"
ACCENT    = "#00C8FF"
ACCENT2   = "#7B2FFF"
TEXT      = "#E8F0FE"
TEXT_DIM  = "#6B7FA3"
BORDER    = "#1E2A42"
BORDER_HL = "#2A3A5A"
# ──────────────────────────────────────────────────────────────────────────────

# Gradient pairs for placeholder backgrounds (per card, cycled by game_id % len)
_PLACEHOLDER_GRADIENTS = [
    ("#0D1F3C", "#1A3A6E"),   # Deep navy
    ("#1A0D3C", "#3A1A6E"),   # Deep violet
    ("#0D2A1F", "#1A5A3A"),   # Deep emerald
    ("#2A1A0D", "#5A3A1A"),   # Deep amber
    ("#2A0D1A", "#6E1A3A"),   # Deep crimson
    ("#0D2A2A", "#1A5A5A"),   # Deep teal
]


def _make_placeholder_pixmap(width: int, height: int,
                              initials: str, game_id: int) -> QPixmap:
    """
    Draw a stylized placeholder cover: gradient background + geometric
    diamond accent + large initials. Pure QPainter, zero extra deps.
    """
    px = QPixmap(width, height)
    px.fill(Qt.GlobalColor.transparent)

    painter = QPainter(px)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    # ── Background gradient ────────────────────────────────────────────────────
    clip_path = QPainterPath()
    clip_path.addRoundedRect(QRectF(0, 0, width, height), 8, 8)
    painter.setClipPath(clip_path)

    grad_pair = _PLACEHOLDER_GRADIENTS[game_id % len(_PLACEHOLDER_GRADIENTS)]
    grad = QLinearGradient(0, 0, width, height)
    grad.setColorAt(0.0, QColor(grad_pair[0]))
    grad.setColorAt(1.0, QColor(grad_pair[1]))
    painter.fillPath(clip_path, QBrush(grad))

    # ── Decorative diamond / hex shape ─────────────────────────────────────────
    cx, cy = width // 2, height // 2
    r = min(width, height) * 0.38

    from PyQt6.QtCore import QPointF
    from PyQt6.QtGui import QPolygonF

    # Outer diamond
    diamond_outer = QPolygonF([
        QPointF(cx,      cy - r),
        QPointF(cx + r,  cy),
        QPointF(cx,      cy + r),
        QPointF(cx - r,  cy),
    ])
    outer_color = QColor(ACCENT)
    outer_color.setAlphaF(0.12)
    painter.setBrush(QBrush(outer_color))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawPolygon(diamond_outer)

    # Inner diamond (ring effect)
    r2 = r * 0.72
    diamond_inner = QPolygonF([
        QPointF(cx,       cy - r2),
        QPointF(cx + r2,  cy),
        QPointF(cx,       cy + r2),
        QPointF(cx - r2,  cy),
    ])
    pen = QPen(QColor(ACCENT))
    pen.setWidthF(1.4)
    pen.setColor(QColor(ACCENT).darker(110))
    outer_color2 = QColor(ACCENT2)
    outer_color2.setAlphaF(0.08)
    painter.setBrush(QBrush(outer_color2))
    painter.setPen(pen)
    painter.drawPolygon(diamond_inner)

    # ── Initials ──────────────────────────────────────────────────────────────
    font_size = int(min(width, height) * 0.32)
    f = QFont("Segoe UI", font_size, QFont.Weight.Black)
    painter.setFont(f)

    # Shadow text
    shadow_color = QColor(0, 0, 0, 80)
    painter.setPen(shadow_color)
    painter.drawText(
        QRectF(2, 2, width, height),
        Qt.AlignmentFlag.AlignCenter, initials
    )

    # Main text with gradient fill
    text_grad = QLinearGradient(cx - 30, cy - 30, cx + 30, cy + 30)
    text_grad.setColorAt(0.0, QColor(ACCENT))
    text_grad.setColorAt(1.0, QColor(ACCENT2))
    painter.setPen(QPen(QBrush(text_grad), 1))
    painter.drawText(
        QRectF(0, 0, width, height),
        Qt.AlignmentFlag.AlignCenter, initials
    )

    painter.end()
    return px


class GameCard(QFrame):
    """Individual game card widget with premium gaming aesthetic."""

    launch_requested = pyqtSignal(int)
    info_requested   = pyqtSignal(int)
    edit_requested   = pyqtSignal(int)  # game_id

    # Dimensions (optimized so 2 rows are fully visible without scrolling)
    CARD_W = 250
    CARD_H = 300
    COVER_W = 190
    COVER_H = 190

    def __init__(self, game_data: dict, parent=None):
        super().__init__(parent)
        self.game_id        = game_data["id"]
        self.game_name      = game_data["name"]
        self.total_playtime = game_data.get("total_playtime_seconds", 0)
        self.last_played    = game_data.get("last_played")
        self.cover_path     = game_data.get("cover_image_path")

        self.setFixedSize(self.CARD_W, self.CARD_H)
        self._hovered = False

        self._setup_ui()
        self._apply_styles()
        self._setup_shadow()

    # ── UI ────────────────────────────────────────────────────────────────────
    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.card = QFrame()
        self.card.setObjectName("cardInner")
        card_l = QVBoxLayout(self.card)
        card_l.setContentsMargins(12, 10, 12, 10)
        card_l.setSpacing(6)

        # Game name (positioned above the 1:1 square cover)
        self.name_label = QLabel(self.game_name)
        self.name_label.setObjectName("gameName")
        self.name_label.setFont(QFont("Rajdhani", 12, QFont.Weight.Bold))
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setMaximumWidth(self.COVER_W)
        self.name_label.setWordWrap(False)
        fm = QFontMetrics(self.name_label.font())
        elided = fm.elidedText(self.game_name, Qt.TextElideMode.ElideRight, self.COVER_W)
        self.name_label.setText(elided)
        card_l.addWidget(self.name_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Cover image / placeholder (1:1 square ratio)
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(self.COVER_W, self.COVER_H)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setObjectName("coverLabel")

        if self.cover_path:
            self._load_cover()
        else:
            initials = self._get_initials()
            px = _make_placeholder_pixmap(self.COVER_W, self.COVER_H, initials, self.game_id)
            self.cover_label.setPixmap(px)

        card_l.addWidget(self.cover_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Info row: playtime + last played
        info_row = QHBoxLayout()
        info_row.setSpacing(0)

        self.playtime_lbl = QLabel(self._fmt_playtime())
        self.playtime_lbl.setFont(QFont("Segoe UI", 8))
        self.playtime_lbl.setObjectName("infoChip")
        self.playtime_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.last_played_lbl = QLabel(self._fmt_last_played())
        self.last_played_lbl.setFont(QFont("Segoe UI", 8))
        self.last_played_lbl.setObjectName("infoChip")
        self.last_played_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        info_row.addWidget(self.playtime_lbl)
        info_row.addStretch()
        info_row.addWidget(self.last_played_lbl)
        card_l.addLayout(info_row)

        # Buttons (Play, Stats, Settings)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.launch_btn = QPushButton("▶  JOUER")
        self.launch_btn.setObjectName("launchBtn")
        self.launch_btn.setFixedHeight(30)
        self.launch_btn.clicked.connect(lambda: self.launch_requested.emit(self.game_id))

        self.info_btn = QPushButton("📊")
        self.info_btn.setObjectName("statsBtn")
        self.info_btn.setFixedSize(30, 30)
        self.info_btn.setToolTip("Statistiques")
        self.info_btn.clicked.connect(lambda: self.info_requested.emit(self.game_id))

        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setObjectName("settingsBtn")
        self.settings_btn.setFixedSize(30, 30)
        self.settings_btn.setToolTip("Paramètres / Modifier")
        self.settings_btn.clicked.connect(lambda: self.edit_requested.emit(self.game_id))

        btn_row.addWidget(self.launch_btn)
        btn_row.addWidget(self.info_btn)
        btn_row.addWidget(self.settings_btn)
        card_l.addLayout(btn_row)

        outer.addWidget(self.card)

    # ── Styles ────────────────────────────────────────────────────────────────
    def _apply_styles(self):
        self.setStyleSheet(f"""
            GameCard {{
                background: transparent;
                border: none;
            }}

            #cardInner {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 12px;
            }}

            #coverLabel {{
                border-radius: 8px;
                background-color: #080B14;
            }}

            #gameName {{
                color: {TEXT};
            }}

            #infoChip {{
                color: {TEXT_DIM};
                padding: 2px 6px;
            }}

            #launchBtn {{
                background-color: {ACCENT};
                color: #000000;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 10px;
                letter-spacing: 1px;
            }}
            #launchBtn:hover {{
                background-color: #33D4FF;
            }}
            #launchBtn:pressed {{
                background-color: #009ECC;
            }}

            #statsBtn {{
                background-color: transparent;
                border: 1px solid {BORDER};
                border-radius: 6px;
                color: {TEXT_DIM};
                font-size: 14px;
            }}
            #statsBtn:hover {{
                border-color: {ACCENT};
                color: {ACCENT};
            }}

            #settingsBtn {{
                background-color: transparent;
                border: 1px solid {BORDER};
                border-radius: 6px;
                color: {TEXT_DIM};
                font-size: 14px;
            }}
            #settingsBtn:hover {{
                border-color: {ACCENT};
                color: {ACCENT};
                background-color: #162438;
            }}
            #settingsBtn:pressed {{
                background-color: #0099CC;
                color: #FFFFFF;
            }}
        """)

    def _setup_shadow(self):
        self._shadow = QGraphicsDropShadowEffect()
        self._shadow.setBlurRadius(18)
        self._shadow.setXOffset(0)
        self._shadow.setYOffset(5)
        self._shadow.setColor(QColor(0, 0, 0, 120))
        self.card.setGraphicsEffect(self._shadow)

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _get_initials(self) -> str:
        words = self.game_name.split()
        if len(words) >= 2:
            return (words[0][0] + words[1][0]).upper()
        elif len(words) == 1 and len(words[0]) >= 2:
            return words[0][:2].upper()
        return "??"

    def _load_cover(self):
        try:
            from pathlib import Path
            if self.cover_path and Path(self.cover_path).exists():
                px = QPixmap(self.cover_path)
                if not px.isNull():
                    size = self.COVER_W
                    dest = QPixmap(size, size)
                    dest.fill(Qt.GlobalColor.transparent)

                    scaled = px.scaled(
                        size, size,
                        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    x = (scaled.width() - size) // 2
                    y = (scaled.height() - size) // 2

                    painter = QPainter(dest)
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

                    path = QPainterPath()
                    path.addRoundedRect(QRectF(0, 0, size, size), 8, 8)
                    painter.setClipPath(path)
                    painter.drawPixmap(0, 0, scaled, x, y, size, size)
                    painter.end()

                    self.cover_label.setPixmap(dest)
                    return
        except Exception as e:
            print(f"Cover load failed: {e}")

        # Fallback if image failed to load
        initials = self._get_initials()
        px = _make_placeholder_pixmap(self.COVER_W, self.COVER_H, initials, self.game_id)
        self.cover_label.setPixmap(px)

    def _fmt_playtime(self) -> str:
        h = self.total_playtime // 3600
        m = (self.total_playtime % 3600) // 60
        return f"⏱ {h}h {m}m" if h > 0 else f"⏱ {m}m"

    def _fmt_last_played(self) -> str:
        if not self.last_played:
            return "Jamais joué"
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(self.last_played)
            return dt.strftime("%d %b")
        except (ValueError, TypeError):
            return str(self.last_played)[:10]

    def update_playtime(self, total_seconds: int):
        self.total_playtime = total_seconds
        self.playtime_lbl.setText(self._fmt_playtime())

    # ── Hover effects ─────────────────────────────────────────────────────────
    def enterEvent(self, event):
        self._hovered = True
        self.card.setStyleSheet(f"""
            #cardInner {{
                background-color: {BG_HOVER};
                border: 1px solid {ACCENT};
                border-radius: 12px;
            }}
        """)
        self._shadow.setColor(QColor(0, 200, 255, 90))
        self._shadow.setBlurRadius(30)
        self._shadow.setYOffset(8)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.card.setStyleSheet(f"""
            #cardInner {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 12px;
            }}
        """)
        self._shadow.setColor(QColor(0, 0, 0, 120))
        self._shadow.setBlurRadius(18)
        self._shadow.setYOffset(5)
        super().leaveEvent(event)
