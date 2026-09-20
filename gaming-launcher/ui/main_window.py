"""
Main Window for Velox Gaming Launcher.

The primary application window featuring:
- Grid view of game cards (3 columns)
- Add game functionality (folder scan or manual)
- Settings access
- System tray integration
- Custom frameless window with premium gaming aesthetic
"""

import sys
import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QFrame, QSystemTrayIcon, QMenu,
    QGraphicsDropShadowEffect, QSizePolicy, QGridLayout
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt6.QtGui import QFont, QColor, QIcon, QLinearGradient, QPainter, QPixmap

from core.database import Database
from core.tracker import get_tracker
from ui.game_card import GameCard
from ui.add_game_dialog import AddGameDialog
from ui.stats_window import StatsWindow
from ui.edit_game_dialog import EditGameDialog
from ui.global_stats_window import GlobalStatsWindow


# ── Design tokens ─────────────────────────────────────────────────────────────
BG_DARK   = "#080B14"   # Main background
BG_SURFACE= "#0F1623"   # Card area / surfaces
BG_RAISED = "#161E2E"   # Elevated elements
ACCENT    = "#00C8FF"   # Electric cyan
ACCENT2   = "#7B2FFF"   # Violet
TEXT      = "#E8F0FE"   # Primary text
TEXT_DIM  = "#6B7FA3"   # Secondary text
BORDER    = "#1E2A42"   # Separator / borders
SUCCESS   = "#00FF88"
DANGER    = "#FF4444"
# ──────────────────────────────────────────────────────────────────────────────


class MainWindow(QMainWindow):
    """Main launcher window with premium gaming aesthetic."""

    # Keep constants for backward compat with other modules
    BG_COLOR      = BG_DARK
    CARD_AREA_BG  = BG_SURFACE
    ACCENT_COLOR  = ACCENT
    TEXT_COLOR    = TEXT

    # Grid columns
    GRID_COLS = 3

    def __init__(self):
        super().__init__()

        self.db      = Database()
        self.tracker = get_tracker()
        self.tracker.add_session_end_callback(self._on_session_end)
        self.tracker.start_tracking()
        self.active_sessions: dict[int, int] = {}
        self._is_shutting_down = False

        # Frameless window
        self.setWindowTitle("Velox Gaming Launcher")
        self.setMinimumSize(1060, 680)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowSystemMenuHint |
            Qt.WindowType.WindowMinMaxButtonsHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        # Drag support for frameless
        self._drag_pos: QPoint | None = None

        ico_file = Path(__file__).parent.parent / "icon" / "velox.ico"
        if ico_file.exists():
            self.setWindowIcon(QIcon(str(ico_file)))

        self._center_window()
        self._setup_ui()
        self._setup_tray()
        self._apply_styles()
        self._refresh_games()

        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._refresh_games)
        self.refresh_timer.start(10000)

    # ── Positioning ───────────────────────────────────────────────────────────
    def _center_window(self):
        """Center the window on the primary screen."""
        screen = QApplication.primaryScreen().geometry()
        size   = self.geometry()
        self.move(
            (screen.width()  - size.width())  // 2,
            (screen.height() - size.height()) // 2,
        )

    # ── UI Setup ──────────────────────────────────────────────────────────────
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Title bar
        root.addWidget(self._create_title_bar())

        # Content area
        content = QFrame()
        content.setObjectName("contentFrame")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(24, 20, 24, 20)
        cl.setSpacing(16)

        # ── Header ────────────────────────────────────────────────────────────
        header = QHBoxLayout()

        title_col = QVBoxLayout()
        title_col.setSpacing(2)

        title_lbl = QLabel("VELOX LAUNCHER")
        title_lbl.setObjectName("mainTitle")
        title_lbl.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))

        sub_lbl = QLabel("Bibliothèque de jeux")
        sub_lbl.setFont(QFont("Segoe UI", 10))
        sub_lbl.setStyleSheet(f"color: {TEXT_DIM};")

        title_col.addWidget(title_lbl)
        title_col.addWidget(sub_lbl)

        # Game count badge (updated after load)
        self.count_badge = QLabel("")
        self.count_badge.setObjectName("countBadge")
        self.count_badge.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.count_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.count_badge.setFixedHeight(24)
        self.count_badge.hide()

        header.addLayout(title_col)
        header.addWidget(self.count_badge, alignment=Qt.AlignmentFlag.AlignBottom)
        header.addStretch()

        self.add_btn = QPushButton("＋  AJOUTER")
        self.add_btn.setObjectName("accentBtn")
        self.add_btn.setFixedHeight(38)
        self.add_btn.clicked.connect(self._add_game)

        self.global_stats_btn = QPushButton("📊")
        self.global_stats_btn.setObjectName("iconBtn")
        self.global_stats_btn.setFixedSize(38, 38)
        self.global_stats_btn.setToolTip("Statistiques globales de la bibliothèque")
        self.global_stats_btn.clicked.connect(self._show_global_stats)

        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setObjectName("iconBtn")
        self.settings_btn.setFixedSize(38, 38)
        self.settings_btn.setToolTip("Paramètres")
        self.settings_btn.clicked.connect(self._show_settings)

        header.addWidget(self.add_btn)
        header.addWidget(self.global_stats_btn)
        header.addWidget(self.settings_btn)
        cl.addLayout(header)

        # Thin separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("separator")
        sep.setFixedHeight(1)
        cl.addWidget(sep)

        # ── Games scroll area ─────────────────────────────────────────────────
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setObjectName("gamesScroll")

        self.games_container = QWidget()
        self.games_container.setObjectName("gamesContainer")
        self.games_layout = QGridLayout(self.games_container)
        self.games_layout.setSpacing(16)
        self.games_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self.scroll_area.setWidget(self.games_container)
        cl.addWidget(self.scroll_area)

        root.addWidget(content)

    def _create_title_bar(self) -> QWidget:
        """Custom draggable title bar."""
        bar = QFrame()
        bar.setObjectName("titleBar")
        bar.setFixedHeight(52)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(18, 0, 12, 0)
        layout.setSpacing(10)

        # Logo with custom transparent emblem (prominent & crisp)
        logo_container = QWidget()
        logo_layout = QHBoxLayout(logo_container)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.setSpacing(10)

        icon_path = Path(__file__).parent.parent / "icon" / "velox_icon_transparent.png"
        if not icon_path.exists():
            icon_path = Path(__file__).parent.parent / "icon" / "velox_icon_transparent.jpg"

        if icon_path.exists():
            logo_img = QLabel()
            logo_img.setObjectName("titleLogoImg")
            pix = QPixmap(str(icon_path))
            if not pix.isNull():
                logo_img.setPixmap(pix.scaled(38, 38, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                logo_img.setFixedSize(38, 38)
                logo_layout.addWidget(logo_img)

        logo_text = QLabel("VELOX")
        logo_text.setObjectName("titleLogo")
        logo_text.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        logo_layout.addWidget(logo_text)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        # Window controls
        power_btn = QPushButton("⏻")
        power_btn.setObjectName("winPowerBtn")
        power_btn.setFixedSize(32, 32)
        power_btn.setToolTip("Éteindre Velox (ferme tous les processus et le systray)")
        power_btn.clicked.connect(self._shutdown_app)

        min_btn = QPushButton("─")
        min_btn.setObjectName("winBtn")
        min_btn.setFixedSize(32, 32)
        min_btn.setToolTip("Réduire dans la barre des tâches")
        min_btn.clicked.connect(self.showMinimized)

        max_btn = QPushButton("□")
        max_btn.setObjectName("winBtn")
        max_btn.setFixedSize(32, 32)
        max_btn.setToolTip("Agrandir / Restaurer")
        max_btn.clicked.connect(self._toggle_maximize)

        close_btn = QPushButton("✕")
        close_btn.setObjectName("winCloseBtn")
        close_btn.setFixedSize(32, 32)
        close_btn.setToolTip("Fermer la fenêtre (Velox reste actif dans le systray)")
        close_btn.clicked.connect(self._close_to_tray)

        layout.addWidget(logo_container)
        layout.addWidget(spacer)
        layout.addWidget(power_btn)
        layout.addSpacing(6)
        layout.addWidget(min_btn)
        layout.addWidget(max_btn)
        layout.addWidget(close_btn)

        # Drag support
        bar.mousePressEvent  = self._on_title_press
        bar.mouseMoveEvent   = self._on_title_move
        bar.mouseDoubleClickEvent = lambda e: self._toggle_maximize()

        return bar

    # ── Drag / window controls ────────────────────────────────────────────────
    def _on_title_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def _on_title_move(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    # ── Tray ──────────────────────────────────────────────────────────────────
    def _setup_tray(self):
        """Set up system tray icon and menu."""
        self.tray_icon = QSystemTrayIcon(self)

        tray_ico = Path(__file__).parent.parent / "icon" / "velox_transparent.ico"
        if not tray_ico.exists():
            tray_ico = Path(__file__).parent.parent / "icon" / "velox_icon_transparent.png"
        if not tray_ico.exists():
            tray_ico = Path(__file__).parent.parent / "icon" / "velox_icon_transparent.jpg"

        if tray_ico.exists():
            self.tray_icon.setIcon(QIcon(str(tray_ico)))
        else:
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            grad = QLinearGradient(0, 0, 32, 32)
            grad.setColorAt(0.0, QColor(ACCENT))
            grad.setColorAt(1.0, QColor(ACCENT2))
            painter.setBrush(grad)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(2, 2, 28, 28)
            painter.setPen(QColor("#000000"))
            painter.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "V")
            painter.end()
            self.tray_icon.setIcon(QIcon(pixmap))

        tray_menu = QMenu()
        tray_menu.addAction("Ouvrir Velox").triggered.connect(self._restore_from_tray)
        tray_menu.addSeparator()
        tray_menu.addAction("⏻ Éteindre Velox").triggered.connect(self._shutdown_app)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.DoubleClick,
            QSystemTrayIcon.ActivationReason.Trigger,
        ):
            if self.isVisible():
                self.hide()
            else:
                self._restore_from_tray()

    # ── Styles ────────────────────────────────────────────────────────────────
    def _apply_styles(self):
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {BG_DARK};
            }}

            #titleBar {{
                background-color: {BG_RAISED};
                border-bottom: 1px solid {BORDER};
            }}

            #titleLogo {{
                color: {ACCENT};
                letter-spacing: 2px;
            }}

            #winBtn {{
                background-color: transparent;
                border: none;
                color: {TEXT_DIM};
                font-size: 15px;
                border-radius: 6px;
            }}
            #winBtn:hover {{
                background-color: {BORDER};
                color: {TEXT};
            }}

            #winPowerBtn {{
                background-color: transparent;
                border: 1px solid #3A1A1A;
                color: #FF5555;
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
            }}
            #winPowerBtn:hover {{
                background-color: #CC2222;
                border-color: #FF4444;
                color: #FFFFFF;
            }}

            #winCloseBtn {{
                background-color: transparent;
                border: none;
                color: {TEXT_DIM};
                font-size: 15px;
                border-radius: 6px;
            }}
            #winCloseBtn:hover {{
                background-color: {DANGER};
                color: #FFFFFF;
            }}

            #contentFrame {{
                background-color: {BG_DARK};
            }}

            #mainTitle {{
                color: {ACCENT};
                letter-spacing: 1px;
            }}

            #countBadge {{
                background-color: {BORDER};
                color: {TEXT_DIM};
                border-radius: 10px;
                padding: 0 10px;
                margin-bottom: 4px;
                margin-left: 8px;
            }}

            #separator {{
                background-color: {BORDER};
                border: none;
            }}

            #accentBtn {{
                background-color: {ACCENT};
                color: #000000;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 11px;
                padding: 0 18px;
                letter-spacing: 1px;
            }}
            #accentBtn:hover {{
                background-color: #33D4FF;
            }}
            #accentBtn:pressed {{
                background-color: #009ECC;
            }}

            #iconBtn {{
                background-color: transparent;
                border: 1px solid {BORDER};
                border-radius: 8px;
                color: {TEXT_DIM};
                font-size: 16px;
            }}
            #iconBtn:hover {{
                border-color: {ACCENT};
                color: {ACCENT};
            }}

            #gamesScroll {{
                border: none;
                background-color: transparent;
            }}

            #gamesContainer {{
                background-color: transparent;
            }}

            QScrollBar:vertical {{
                background-color: transparent;
                width: 6px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {BORDER};
                border-radius: 3px;
                min-height: 24px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {ACCENT};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
            }}

            QLabel {{
                color: {TEXT};
            }}
        """)

    # ── Games list ────────────────────────────────────────────────────────────
    def _refresh_games(self):
        """Refresh the games grid from database."""
        # Clear grid
        while self.games_layout.count():
            item = self.games_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        games = self.db.get_all_games()

        if not games:
            empty = QLabel(
                "Aucun jeu ajouté.\n\nCliquez sur  ＋ AJOUTER  pour commencer !"
            )
            empty.setFont(QFont("Segoe UI", 13))
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"color: {TEXT_DIM}; padding: 60px;")
            self.games_layout.addWidget(empty, 0, 0, 1, self.GRID_COLS)
            self.count_badge.hide()
        else:
            for idx, game_data in enumerate(games):
                row = idx // self.GRID_COLS
                col = idx % self.GRID_COLS
                card = GameCard(game_data)
                card.launch_requested.connect(self._launch_game)
                card.info_requested.connect(self._show_stats)
                card.edit_requested.connect(self._open_game_settings)
                self.games_layout.addWidget(card, row, col)

            # Update badge
            n = len(games)
            self.count_badge.setText(f"  {n} jeu{'x' if n > 1 else ''}  ")
            self.count_badge.show()

    # ── Game actions ──────────────────────────────────────────────────────────
    def _add_game(self):
        """Show dialog to add a new game (single or bulk via folder scan)."""
        dialog = AddGameDialog(self)

        if dialog.exec() != AddGameDialog.DialogCode.Accepted:
            return

        mode = dialog.get_mode()

        if mode == "scan":
            games_to_add = dialog.get_scan_results()
            for data in games_to_add:
                self.db.add_game(
                    name=data["name"],
                    exe_path=data["exe_path"],
                    cover_image_path=data["cover_image_path"],
                )
        else:
            data = dialog.get_game_data()
            self.db.add_game(
                name=data["name"],
                exe_path=data["exe_path"],
                cover_image_path=data["cover_image_path"],
            )

        self._refresh_games()

    def _launch_game(self, game_id: int):
        """Launch a game and start tracking."""
        game_data = self.db.get_game(game_id)
        if not game_data:
            return

        exe_path = game_data["exe_path"]
        if not os.path.exists(exe_path):
            print(f"Executable not found: {exe_path}")
            return

        session_id = self.db.start_session(game_id)
        self.active_sessions[game_id] = session_id

        pid = self.tracker.launch_and_track(exe_path, game_id)
        if pid:
            print(f"Launched {game_data['name']} (PID: {pid})")
        else:
            self.db.end_session(session_id)
            del self.active_sessions[game_id]

    def _on_session_end(self, game_id: int, pid: int):
        """Called when a tracked game process ends."""
        if game_id in self.active_sessions:
            session_id = self.active_sessions.pop(game_id)
            self.db.end_session(session_id)
            from PyQt6.QtCore import QMetaObject, Qt
            QMetaObject.invokeMethod(
                self, "_refresh_games",
                Qt.ConnectionType.QueuedConnection,
            )

    def _show_stats(self, game_id: int):
        """Show statistics window for a game."""
        game_data = self.db.get_game(game_id)
        if game_data:
            stats_window = StatsWindow(game_data, self.db, self)
            stats_window.show()

    def _open_game_settings(self, game_id: int):
        """Open settings dialog for a game to edit name, cover or delete."""
        game_data = self.db.get_game(game_id)
        if not game_data:
            return

        dialog = EditGameDialog(game_data, self)
        if dialog.exec() == EditGameDialog.DialogCode.Accepted:
            if dialog.is_deleted():
                self.db.delete_game(game_id)
                cover = game_data.get("cover_image_path")
                if cover:
                    from pathlib import Path
                    icon_file = Path(cover)
                    if icon_file.exists() and "game_icons" in str(icon_file):
                        try:
                            icon_file.unlink()
                        except OSError:
                            pass
                self._refresh_games()
            else:
                updated = dialog.get_game_data()
                self.db.update_game(
                    game_id=game_id,
                    name=updated["name"],
                    cover_image_path=updated["cover_image_path"]
                )
                self._refresh_games()

    def _show_global_stats(self):
        """Show the global statistics window."""
        stats_window = GlobalStatsWindow(self.db, self)
        stats_window.show()

    def _show_settings(self):
        """Show settings dialog (placeholder)."""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            self, "Paramètres",
            "Panneau de paramètres (à venir).\n\n"
            "• Couleur d'accent personnalisable\n"
            "• Minimiser dans la barre système\n"
            "• Préférences de polices",
        )

    # ── Close & Shutdown ──────────────────────────────────────────────────────
    def _close_to_tray(self):
        """Close/hide window immediately and keep system tray running."""
        self.hide()

    def _restore_from_tray(self):
        """Restore window from system tray."""
        self._refresh_games()
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _shutdown_app(self):
        """Completely shut down the application, tracker, systray, and all processes."""
        self._is_shutting_down = True

        # Stop tracker
        if hasattr(self, "tracker") and self.tracker:
            self.tracker.stop_tracking()

        # End any active sessions in DB
        for game_id, session_id in list(self.active_sessions.items()):
            try:
                self.db.end_session(session_id)
            except Exception:
                pass
        self.active_sessions.clear()

        # Close database
        if hasattr(self, "db") and self.db:
            self.db.close()

        # Hide and delete systray icon so it immediately disappears
        if hasattr(self, "tray_icon") and self.tray_icon:
            self.tray_icon.hide()
            self.tray_icon.deleteLater()

        # Quit application completely
        self.close()
        QApplication.quit()

    def closeEvent(self, event):
        if not getattr(self, "_is_shutting_down", False):
            # Window close button used: only hide window, keep systray running!
            event.ignore()
            self._close_to_tray()
        else:
            event.accept()


# ── Entry point ───────────────────────────────────────────────────────────────
def main(app=None):
    if app is None:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        app = QApplication(sys.argv)
        app.setApplicationName("Velox Gaming Launcher")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
