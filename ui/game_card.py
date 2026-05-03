"""
Game Card widget for the Gaming Launcher.
A compact card that displays game info: cover image, name, playtime, last played.
Includes Launch/Stop and Info action buttons.
Features: hover glow effect, lazy-loaded cover image, neon accent styling.
"""

import os
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsDropShadowEffect, QSizePolicy
)
from PyQt6.QtGui import QPixmap, QColor, QPainter, QLinearGradient, QIcon
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPropertyAnimation, QByteArray
from PyQt6.QtSvg import QSvgRenderer

from core.models import Game, format_playtime, format_last_played
from ui.icons import ICON_PLAY, ICON_STOP, ICON_INFO, colorize


# Card dimensions
CARD_WIDTH = 200
CARD_HEIGHT = 290
COVER_HEIGHT = 160


class GameCard(QFrame):
    """
    Individual game card widget.
    Emits signals when the user clicks Launch, Stop, or Info.
    """

    launch_clicked = pyqtSignal(Game)
    stop_clicked = pyqtSignal(Game)
    info_clicked = pyqtSignal(Game)

    def __init__(self, game: Game, accent: str = "#00D4FF", parent=None):
        super().__init__(parent)
        self._game = game
        self._accent = accent
        self._is_tracking = False
        self._cover_loaded = False

        self.setObjectName("gameCard")
        self.setFixedSize(CARD_WIDTH, CARD_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Glow shadow effect (hidden by default, shown on hover)
        self._glow = QGraphicsDropShadowEffect(self)
        self._glow.setBlurRadius(0)
        self._glow.setColor(QColor(accent))
        self._glow.setOffset(0, 0)
        self.setGraphicsEffect(self._glow)

        self._build_ui()

    # ── UI Construction ────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(4)

        # Cover image label
        self._cover_label = QLabel()
        self._cover_label.setFixedSize(CARD_WIDTH, COVER_HEIGHT)
        self._cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cover_label.setStyleSheet(
            "border-top-left-radius: 10px; "
            "border-top-right-radius: 10px; "
            "background-color: #1A1A2E;"
        )
        layout.addWidget(self._cover_label)

        # Info section
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(10, 4, 10, 0)
        info_layout.setSpacing(2)

        # Game name
        self._name_label = QLabel(self._game.name)
        self._name_label.setStyleSheet(
            f"font-size: 15px; font-weight: 700; color: #E8E8F0;"
        )
        self._name_label.setWordWrap(True)
        self._name_label.setMaximumHeight(40)
        info_layout.addWidget(self._name_label)

        # Playtime
        playtime_text = format_playtime(self._game.total_playtime_seconds)
        self._playtime_label = QLabel(f"⏱ {playtime_text}")
        self._playtime_label.setStyleSheet(
            f"font-size: 12px; color: {self._accent}; font-weight: 600;"
        )
        info_layout.addWidget(self._playtime_label)

        # Last played
        last_text = format_last_played(self._game.last_played)
        self._last_played_label = QLabel(f"Last: {last_text}")
        self._last_played_label.setStyleSheet(
            "font-size: 11px; color: #8888AA;"
        )
        info_layout.addWidget(self._last_played_label)

        layout.addLayout(info_layout)
        layout.addStretch()

        # Action buttons row
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(8, 0, 8, 0)
        btn_layout.setSpacing(6)

        # Launch / Stop button
        self._launch_btn = QPushButton("PLAY")
        self._launch_btn.setObjectName("accentBtn")
        self._launch_btn.setFixedHeight(30)
        self._launch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._launch_btn.clicked.connect(self._on_launch)
        btn_layout.addWidget(self._launch_btn, stretch=2)

        # Info button
        self._info_btn = QPushButton("INFO")
        self._info_btn.setFixedHeight(30)
        self._info_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._info_btn.clicked.connect(self._on_info)
        btn_layout.addWidget(self._info_btn, stretch=1)

        layout.addLayout(btn_layout)

    # ── Cover Image (Lazy Loading) ─────────────────────────────────────

    def load_cover(self):
        """
        Load the cover image — called only when the card becomes visible.
        Scales the image to card size to minimize memory usage.
        """
        if self._cover_loaded:
            return

        self._cover_loaded = True
        pixmap = None

        # Try loading user-provided cover image
        if self._game.cover_image_path and os.path.isfile(
                self._game.cover_image_path):
            pixmap = QPixmap(self._game.cover_image_path)

        # If no cover image, generate a gradient placeholder with initials
        if pixmap is None or pixmap.isNull():
            pixmap = self._generate_placeholder()

        # Scale to fit the cover area, preserving aspect ratio
        scaled = pixmap.scaled(
            CARD_WIDTH, COVER_HEIGHT,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )
        # Crop to exact size
        if scaled.width() > CARD_WIDTH or scaled.height() > COVER_HEIGHT:
            x = (scaled.width() - CARD_WIDTH) // 2
            y = (scaled.height() - COVER_HEIGHT) // 2
            scaled = scaled.copy(x, y, CARD_WIDTH, COVER_HEIGHT)

        self._cover_label.setPixmap(scaled)

    def _generate_placeholder(self) -> QPixmap:
        """Generate a gradient placeholder with game initials."""
        pixmap = QPixmap(CARD_WIDTH, COVER_HEIGHT)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw gradient background
        gradient = QLinearGradient(0, 0, CARD_WIDTH, COVER_HEIGHT)
        gradient.setColorAt(0, QColor("#1A1A2E"))
        gradient.setColorAt(1, QColor(self._accent).darker(300))
        painter.fillRect(pixmap.rect(), gradient)

        # Draw initials
        initials = "".join(
            w[0].upper() for w in self._game.name.split()[:2]
        ) or "?"
        font = painter.font()
        font.setPixelSize(48)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(self._accent))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, initials)

        painter.end()
        return pixmap

    # ── State Updates ──────────────────────────────────────────────────

    def set_tracking(self, tracking: bool):
        """Update the card to reflect whether the game is currently tracked."""
        self._is_tracking = tracking
        if tracking:
            self._launch_btn.setText("STOP")
            self._launch_btn.setObjectName("accentBtn")
            self._launch_btn.setStyleSheet(
                f"background-color: #CC3333; color: white; "
                f"border: none; border-radius: 6px; font-weight: 700;"
            )
        else:
            self._launch_btn.setText("PLAY")
            self._launch_btn.setObjectName("accentBtn")
            self._launch_btn.setStyleSheet("")  # Reset to theme default

    def update_game_data(self, game: Game):
        """Refresh displayed data after a session ends or game is edited."""
        self._game = game
        self._name_label.setText(game.name)
        self._playtime_label.setText(
            f"⏱ {format_playtime(game.total_playtime_seconds)}"
        )
        self._last_played_label.setText(
            f"Last: {format_last_played(game.last_played)}"
        )

    @property
    def game(self) -> Game:
        return self._game

    # ── Hover Glow Animation ───────────────────────────────────────────

    def enterEvent(self, event):
        """Animate glow effect on mouse enter."""
        self._glow.setBlurRadius(25)
        self._glow.setColor(QColor(self._accent))
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Remove glow on mouse leave."""
        self._glow.setBlurRadius(0)
        super().leaveEvent(event)

    # ── Signal Handlers ────────────────────────────────────────────────

    def _on_launch(self):
        if self._is_tracking:
            self.stop_clicked.emit(self._game)
        else:
            self.launch_clicked.emit(self._game)

    def _on_info(self):
        self.info_clicked.emit(self._game)
