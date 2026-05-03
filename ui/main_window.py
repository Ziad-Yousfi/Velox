"""
Main Window for the Gaming Launcher.
Features:
  - Frameless window with custom title bar (drag to move, min/max/close)
  - Grid of game cards with lazy-loaded covers
  - System tray icon with right-click context menu
  - Settings dialog (accent color, minimize-to-tray)
  - Scanline grid overlay painted on the background
"""

import json
import os
import sys

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QGridLayout, QSystemTrayIcon,
    QMenu, QDialog, QCheckBox, QFrame, QSizePolicy,
    QMessageBox, QApplication, QSpacerItem
)
from PyQt6.QtGui import (
    QIcon, QPixmap, QPainter, QColor, QPen, QAction,
    QMouseEvent, QCursor, QFontDatabase
)
from PyQt6.QtCore import (
    Qt, QPoint, QTimer, QSize, pyqtSignal, QEvent
)

from core.database import Database
from core.tracker import GameTracker
from core.models import Game
from ui.game_card import GameCard
from ui.theme import generate_stylesheet
from ui.icons import (
    ICON_PLUS, ICON_SETTINGS, ICON_CLOSE, ICON_MINIMIZE,
    ICON_MAXIMIZE, ICON_GAMEPAD, ICON_DELETE, ICON_INFO, colorize
)


# ── Helper: create QIcon from SVG string ───────────────────────────────

def svg_to_icon(svg_template: str, color: str, size: int = 24) -> QIcon:
    """Render an SVG template string into a QIcon."""
    from PyQt6.QtSvg import QSvgRenderer
    from PyQt6.QtCore import QByteArray

    svg_data = colorize(svg_template, color).encode("utf-8")
    renderer = QSvgRenderer(QByteArray(svg_data))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


def get_base_dir() -> str:
    """Get the application's base directory (works for dev and PyInstaller)."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_settings_path() -> str:
    return os.path.join(get_base_dir(), "settings.json")


def load_settings() -> dict:
    defaults = {"accent_color": "#00D4FF", "minimize_to_tray": True}
    path = get_settings_path()
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                defaults.update(json.load(f))
        except (json.JSONDecodeError, IOError):
            pass
    return defaults


def save_settings(settings: dict):
    path = get_settings_path()
    try:
        with open(path, "w") as f:
            json.dump(settings, f, indent=2)
    except IOError:
        pass


# ═══════════════════════════════════════════════════════════════════════
#  CUSTOM TITLE BAR
# ═══════════════════════════════════════════════════════════════════════

class TitleBar(QWidget):
    """Custom frameless title bar with drag-to-move and window controls."""

    def __init__(self, accent: str, parent=None):
        super().__init__(parent)
        self._accent = accent
        self._drag_pos = None
        self.setObjectName("titleBar")
        self.setFixedHeight(40)
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 4, 0)
        layout.setSpacing(8)

        # App icon + title
        icon_label = QLabel("🎮")
        icon_label.setStyleSheet("font-size: 18px;")
        layout.addWidget(icon_label)

        title = QLabel("VAULTEX LAUNCHER")
        title.setStyleSheet(
            f"font-size: 14px; font-weight: 700; "
            f"color: {self._accent}; letter-spacing: 2px;"
        )
        layout.addWidget(title)
        layout.addStretch()

        # Window control buttons
        for btn_name, icon_svg, obj_name in [
            ("min", ICON_MINIMIZE, "titleBtn"),
            ("max", ICON_MAXIMIZE, "titleBtn"),
            ("close", ICON_CLOSE, "closeBtn"),
        ]:
            btn = QPushButton()
            btn.setObjectName(obj_name)
            btn.setIcon(svg_to_icon(icon_svg, "#AAAACC"))
            btn.setIconSize(QSize(16, 16))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            layout.addWidget(btn)
            setattr(self, f"_{btn_name}_btn", btn)

        # Connect window control signals
        self._min_btn.clicked.connect(
            lambda: self.window().showMinimized()
        )
        self._max_btn.clicked.connect(self._toggle_maximize)
        self._close_btn.clicked.connect(
            lambda: self.window().close()
        )

    def _toggle_maximize(self):
        win = self.window()
        if win.isMaximized():
            win.showNormal()
        else:
            win.showMaximized()

    # Drag-to-move support
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - \
                             self.window().frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.window().move(
                event.globalPosition().toPoint() - self._drag_pos
            )
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        self._toggle_maximize()


# ═══════════════════════════════════════════════════════════════════════
#  SETTINGS DIALOG
# ═══════════════════════════════════════════════════════════════════════

class SettingsDialog(QDialog):
    """Simple settings popup: accent color + minimize-to-tray toggle."""

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self._settings = dict(settings)
        self.setWindowTitle("Settings")
        self.setFixedSize(380, 260)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint
        )
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("SETTINGS")
        accent = self._settings.get("accent_color", "#00D4FF")
        title.setStyleSheet(
            f"font-size: 20px; font-weight: 700; color: {accent};"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #222233;")
        layout.addWidget(sep)

        # Accent color selection
        color_label = QLabel("Accent Color")
        color_label.setStyleSheet("font-weight: 600;")
        layout.addWidget(color_label)

        color_row = QHBoxLayout()
        self._color_buttons = {}
        colors = {
            "Electric Blue": "#00D4FF",
            "Neon Green": "#00FF88",
            "Neon Pink": "#FF0080",
            "Neon Purple": "#AA00FF",
            "Neon Orange": "#FF8800",
        }
        for name, hex_color in colors.items():
            btn = QPushButton()
            btn.setFixedSize(36, 36)
            btn.setToolTip(name)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            selected = "3px solid white" if hex_color == accent else "none"
            btn.setStyleSheet(
                f"background-color: {hex_color}; border: {selected}; "
                f"border-radius: 18px;"
            )
            btn.clicked.connect(
                lambda checked, c=hex_color: self._select_color(c)
            )
            color_row.addWidget(btn)
            self._color_buttons[hex_color] = btn

        layout.addLayout(color_row)

        # Minimize to tray toggle
        self._tray_check = QCheckBox("Minimize to tray on close")
        self._tray_check.setChecked(
            self._settings.get("minimize_to_tray", True)
        )
        layout.addWidget(self._tray_check)

        layout.addStretch()

        # Save button
        save_btn = QPushButton("Save")
        save_btn.setObjectName("accentBtn")
        save_btn.setFixedHeight(36)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self._on_save)
        layout.addWidget(save_btn)

    def _select_color(self, color: str):
        self._settings["accent_color"] = color
        # Update button borders
        for hex_color, btn in self._color_buttons.items():
            sel = "3px solid white" if hex_color == color else "none"
            btn.setStyleSheet(
                f"background-color: {hex_color}; border: {sel}; "
                f"border-radius: 18px;"
            )

    def _on_save(self):
        self._settings["minimize_to_tray"] = self._tray_check.isChecked()
        self.accept()

    def get_settings(self) -> dict:
        return self._settings


# ═══════════════════════════════════════════════════════════════════════
#  BACKGROUND WIDGET — Scanline grid overlay
# ═══════════════════════════════════════════════════════════════════════

class BackgroundWidget(QWidget):
    """
    Central widget that paints a subtle scanline / grid overlay.
    Lightweight: drawn via QPainter, no image file.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("centralBg")

    def paintEvent(self, event):
        painter = QPainter(self)
        # Background fill
        painter.fillRect(self.rect(), QColor("#0D0D0D"))

        # Draw subtle grid lines every 40px
        pen = QPen(QColor(255, 255, 255, 8))  # Very faint white
        pen.setWidth(1)
        painter.setPen(pen)

        step = 40
        w, h = self.width(), self.height()
        for x in range(0, w, step):
            painter.drawLine(x, 0, x, h)
        for y in range(0, h, step):
            painter.drawLine(0, y, w, y)

        painter.end()


# ═══════════════════════════════════════════════════════════════════════
#  MAIN WINDOW
# ═══════════════════════════════════════════════════════════════════════

class MainWindow(QMainWindow):
    """
    Primary launcher window.
    Manages the game grid, tray icon, tracker, and navigation.
    """

    def __init__(self, settings: dict = None, parent=None):
        super().__init__(parent)
        self._settings = settings or load_settings()
        self._accent = self._settings.get("accent_color", "#00D4FF")

        # Initialize database and tracker
        db_path = os.path.join(get_base_dir(), "launcher.db")
        self._db = Database(db_path)
        self._tracker = GameTracker(self._db, self)
        self._tracker.session_started.connect(self._on_session_started)
        self._tracker.session_ended.connect(self._on_session_ended)

        # Card references: game_id → GameCard
        self._cards: dict[int, GameCard] = {}
        self._is_minimized_to_tray = False

        # Window setup — frameless
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setMinimumSize(800, 560)
        self.resize(960, 640)
        self.setWindowTitle("Vaultex Launcher")

        # Apply theme stylesheet
        self.setStyleSheet(generate_stylesheet(self._accent))

        self._build_ui()
        self._setup_tray()
        self._load_games()

    # ── UI Construction ────────────────────────────────────────────────

    def _build_ui(self):
        # Central widget with scanline background
        central = BackgroundWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Custom title bar
        self._title_bar = TitleBar(self._accent)
        root_layout.addWidget(self._title_bar)

        # Content area
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 12, 16, 12)
        content_layout.setSpacing(12)

        # Toolbar: section title + action buttons
        toolbar = QHBoxLayout()

        section_title = QLabel("MY GAMES")
        section_title.setObjectName("sectionTitle")
        toolbar.addWidget(section_title)
        toolbar.addStretch()

        # Library Info button (global stats for all games)
        lib_info_btn = QPushButton("  LIBRARY INFO")
        lib_info_btn.setIcon(svg_to_icon(ICON_INFO, self._accent))
        lib_info_btn.setIconSize(QSize(18, 18))
        lib_info_btn.setFixedHeight(36)
        lib_info_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        lib_info_btn.setToolTip("View combined stats for all games")
        lib_info_btn.clicked.connect(self._show_global_stats)
        toolbar.addWidget(lib_info_btn)

        # Batch add games button
        batch_btn = QPushButton("  BATCH ADD")
        batch_btn.setIcon(svg_to_icon(ICON_PLUS, "#00FF88"))
        batch_btn.setIconSize(QSize(18, 18))
        batch_btn.setFixedHeight(36)
        batch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        batch_btn.setToolTip("Add multiple games at once or drag & drop")
        batch_btn.clicked.connect(self._batch_add_games)
        toolbar.addWidget(batch_btn)

        # Add single game button
        add_btn = QPushButton("  ADD GAME")
        add_btn.setIcon(svg_to_icon(ICON_PLUS, self._accent))
        add_btn.setIconSize(QSize(18, 18))
        add_btn.setFixedHeight(36)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self._add_game)
        toolbar.addWidget(add_btn)

        # Settings button
        settings_btn = QPushButton()
        settings_btn.setIcon(svg_to_icon(ICON_SETTINGS, "#AAAACC"))
        settings_btn.setIconSize(QSize(20, 20))
        settings_btn.setFixedSize(36, 36)
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.setToolTip("Settings")
        settings_btn.clicked.connect(self._open_settings)
        toolbar.addWidget(settings_btn)

        content_layout.addLayout(toolbar)

        # Scroll area for game cards grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self._grid_container = QWidget()
        self._grid_container.setStyleSheet("background: transparent;")
        self._grid_layout = QGridLayout(self._grid_container)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self._grid_layout.setSpacing(16)
        self._grid_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        scroll.setWidget(self._grid_container)

        # Connect scroll for lazy loading
        scroll.verticalScrollBar().valueChanged.connect(
            self._on_scroll_changed
        )
        self._scroll_area = scroll

        content_layout.addWidget(scroll)

        # Empty state label
        self._empty_label = QLabel(
            "No games added yet.\nClick \"ADD GAME\" to get started!"
        )
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(
            "color: #555566; font-size: 16px; padding: 60px;"
        )
        self._empty_label.setVisible(False)
        content_layout.addWidget(self._empty_label)

        root_layout.addWidget(content)

        # Enable drag & drop on main window
        self.setAcceptDrops(True)

    # ── System Tray ────────────────────────────────────────────────────

    def _setup_tray(self):
        """Create the system tray icon with a context menu."""
        self._tray = QSystemTrayIcon(self)
        self._tray.setIcon(svg_to_icon(ICON_GAMEPAD, self._accent, 64))
        self._tray.setToolTip("Vaultex Launcher")

        tray_menu = QMenu()
        tray_menu.setStyleSheet(
            "QMenu { background: #1A1A2E; color: #E8E8F0; border: 1px solid #222233; }"
            "QMenu::item:selected { background: #00D4FF; color: #0D0D0D; }"
        )

        open_action = QAction("Open Launcher", self)
        open_action.triggered.connect(self._restore_from_tray)
        tray_menu.addAction(open_action)

        tray_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self._force_quit)
        tray_menu.addAction(exit_action)

        self._tray.setContextMenu(tray_menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._restore_from_tray()

    def _restore_from_tray(self):
        self._is_minimized_to_tray = False
        self.showNormal()
        self.activateWindow()

    def _minimize_to_tray(self):
        self._is_minimized_to_tray = True
        self.hide()

    # ── Game Grid ──────────────────────────────────────────────────────

    def _load_games(self):
        """Fetch games from DB and populate the grid."""
        games = self._db.get_all_games()

        # Clear existing cards
        for card in self._cards.values():
            card.setParent(None)
            card.deleteLater()
        self._cards.clear()

        # Clear grid layout
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not games:
            self._empty_label.setVisible(True)
            self._scroll_area.setVisible(False)
            return

        self._empty_label.setVisible(False)
        self._scroll_area.setVisible(True)

        cols = max(1, (self.width() - 48) // 220)

        for idx, game in enumerate(games):
            card = GameCard(game, self._accent)
            card.launch_clicked.connect(self._on_launch_game)
            card.stop_clicked.connect(self._on_stop_game)
            card.info_clicked.connect(self._on_show_stats)

            # Set tracking state if already tracking
            if self._tracker.is_tracking(game.id):
                card.set_tracking(True)

            row = idx // cols
            col = idx % cols
            self._grid_layout.addWidget(card, row, col)
            self._cards[game.id] = card

        # Trigger lazy loading for visible cards
        QTimer.singleShot(100, self._lazy_load_visible)

    def _on_scroll_changed(self):
        """Trigger lazy loading when the user scrolls."""
        self._lazy_load_visible()

    def _lazy_load_visible(self):
        """Load cover images only for cards visible in the viewport."""
        viewport = self._scroll_area.viewport()
        viewport_rect = viewport.rect()

        for card in self._cards.values():
            # Map card position to viewport coordinates
            card_pos = card.mapTo(viewport, QPoint(0, 0))
            card_rect = card.rect().translated(card_pos)
            if viewport_rect.intersects(card_rect):
                card.load_cover()

    def resizeEvent(self, event):
        """Re-layout grid when window is resized."""
        super().resizeEvent(event)
        if self._cards:
            self._relayout_grid()

    def _relayout_grid(self):
        """Re-arrange cards in the grid based on current window width."""
        cards = list(self._cards.values())
        cols = max(1, (self.width() - 48) // 220)

        # Remove all from layout (don't delete)
        while self._grid_layout.count():
            self._grid_layout.takeAt(0)

        for idx, card in enumerate(cards):
            row = idx // cols
            col = idx % cols
            self._grid_layout.addWidget(card, row, col)

        QTimer.singleShot(50, self._lazy_load_visible)

    # ── Game Actions ───────────────────────────────────────────────────

    def _add_game(self):
        # Lazy import to reduce startup RAM
        from ui.add_game_dialog import AddGameDialog
        dialog = AddGameDialog(self._accent, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_result()
            self._db.add_game(
                data["name"], data["exe_path"], data["cover_image_path"]
            )
            self._load_games()

    def _batch_add_games(self):
        """Open batch add dialog to add multiple games at once."""
        from ui.batch_add_dialog import BatchAddDialog
        dialog = BatchAddDialog(self._accent, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            results = dialog.get_results()
            for data in results:
                self._db.add_game(
                    data["name"], data["exe_path"], data["cover_image_path"]
                )
            if results:
                self._load_games()

    def _show_global_stats(self):
        """Show aggregated stats for all games in the library."""
        from ui.global_stats_window import GlobalStatsWindow
        dialog = GlobalStatsWindow(self._db, self._accent, self)
        dialog.exec()

    def _on_launch_game(self, game: Game):
        success = self._tracker.launch_game(game)
        if success and game.id in self._cards:
            self._cards[game.id].set_tracking(True)
        elif not success:
            QMessageBox.warning(
                self, "Launch Error",
                f"Failed to launch:\n{game.exe_path}\n\n"
                "Make sure the file exists and is accessible."
            )

    def _on_stop_game(self, game: Game):
        self._tracker.stop_tracking(game.id)
        if game.id in self._cards:
            self._cards[game.id].set_tracking(False)

    def _on_show_stats(self, game: Game):
        # Lazy import to reduce startup RAM
        from ui.stats_window import StatsWindow
        # Refresh game data before showing stats
        updated_game = self._db.get_game(game.id)
        if updated_game:
            stats = StatsWindow(updated_game, self._db, self._accent, self)
            stats.exec()

    def _on_session_started(self, game_id: int, session_id: int):
        if game_id in self._cards:
            self._cards[game_id].set_tracking(True)

    def _on_session_ended(self, game_id: int, session_id: int, duration: int):
        """Refresh card data when a session ends."""
        if game_id in self._cards:
            self._cards[game_id].set_tracking(False)
            updated = self._db.get_game(game_id)
            if updated:
                self._cards[game_id].update_game_data(updated)

    # ── Settings ───────────────────────────────────────────────────────

    def _open_settings(self):
        dialog = SettingsDialog(self._settings, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_settings = dialog.get_settings()
            self._settings = new_settings
            self._accent = new_settings.get("accent_color", "#00D4FF")
            save_settings(new_settings)
            # Re-apply theme with new accent
            self.setStyleSheet(generate_stylesheet(self._accent))
            self._load_games()

    # ── Close Behavior ─────────────────────────────────────────────────

    def closeEvent(self, event):
        """
        On close:
        - If minimize_to_tray is enabled AND games are tracking → minimize
        - Otherwise → quit (but finalize active sessions first)
        """
        minimize = self._settings.get("minimize_to_tray", True)
        has_active = self._tracker.has_active_sessions()

        if minimize and has_active:
            event.ignore()
            self._minimize_to_tray()
            self._tray.showMessage(
                "Vaultex Launcher",
                "Tracking continues in background. "
                "Right-click tray icon to exit.",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
        else:
            self._tracker.stop_all()
            self._db.close()
            self._tray.hide()
            event.accept()

    def _force_quit(self):
        """Force quit from tray menu — end all sessions and exit."""
        self._tracker.stop_all()
        self._db.close()
        self._tray.hide()
        QApplication.quit()

    # ── Context menu for game cards (right-click to delete) ────────────

    def contextMenuEvent(self, event):
        """Right-click on a card to delete the game."""
        pos = event.globalPos()
        for game_id, card in self._cards.items():
            if card.geometry().contains(card.mapFromGlobal(pos)):
                menu = QMenu(self)
                menu.setStyleSheet(
                    "QMenu { background: #1A1A2E; color: #E8E8F0; "
                    "border: 1px solid #222233; }"
                    "QMenu::item:selected { background: #CC3333; }"
                )
                delete_action = menu.addAction("Delete Game")
                action = menu.exec(pos)
                if action == delete_action:
                    reply = QMessageBox.question(
                        self, "Delete Game",
                        f"Delete '{card.game.name}' and all its data?",
                        QMessageBox.StandardButton.Yes
                        | QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        if self._tracker.is_tracking(game_id):
                            self._tracker.stop_tracking(game_id)
                        self._db.delete_game(game_id)
                        self._load_games()
                break

    # ── Drag & Drop on Main Window ─────────────────────────────────────

    def dragEnterEvent(self, event):
        """Accept file drops on the main window."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """
        Handle files dropped on the main window.
        Resolves .exe and .lnk files, adds them directly to the library.
        """
        import os
        # Lazy import to reduce RAM — only loaded on first drop
        from ui.batch_add_dialog import _resolve_file_path

        paths = []
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            resolved = _resolve_file_path(file_path)
            if resolved:
                paths.append(resolved)
            elif os.path.isdir(file_path):
                for fname in os.listdir(file_path):
                    fpath = os.path.join(file_path, fname)
                    resolved = _resolve_file_path(fpath)
                    if resolved:
                        paths.append(resolved)

        if not paths:
            return

        # Avoid duplicate exe paths
        existing_games = self._db.get_all_games()
        existing_paths = {g.exe_path for g in existing_games}

        added = 0
        for path in paths:
            if path not in existing_paths:
                # Auto-generate name from filename
                basename = os.path.splitext(os.path.basename(path))[0]
                for suffix in ["-Win64-Shipping", "_x64", "_x86", "-Win64"]:
                    basename = basename.replace(suffix, "")
                name = basename.replace("_", " ").title()
                
                self._db.add_game(name, path, None)
                existing_paths.add(path)
                added += 1

        if added > 0:
            self._load_games()

        event.acceptProposedAction()
