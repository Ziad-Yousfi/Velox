"""
Main Window for Velox Gaming Launcher.

The primary application window featuring:
- Grid view of game cards
- Add game functionality
- Settings access
- System tray integration
- Custom frameless window with gaming aesthetic
"""

import sys
import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QFrame, QSystemTrayIcon, QMenu,
    QGraphicsDropShadowEffect, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QColor, QIcon, QCursor

from core.database import Database
from core.tracker import get_tracker
from ui.game_card import GameCard
from ui.add_game_dialog import AddGameDialog
from ui.stats_window import StatsWindow


class MainWindow(QMainWindow):
    """Main launcher window with gaming aesthetic."""
    
    # Styling constants
    BG_COLOR = "#0D0D0D"
    CARD_AREA_BG = "#111111"
    ACCENT_COLOR = "#00D4FF"
    TEXT_COLOR = "#FFFFFF"
    
    def __init__(self):
        super().__init__()
        
        self.db = Database()
        self.tracker = get_tracker()
        
        # Set up tracker callback
        self.tracker.add_session_end_callback(self._on_session_end)
        
        # Start tracker
        self.tracker.start_tracking()
        
        # Track active sessions
        self.active_sessions = {}  # game_id -> session_id
        
        # Window setup
        self.setWindowTitle("Velox Gaming Launcher")
        self.setMinimumSize(1000, 700)
        
        # Frameless window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowSystemMenuHint |
            Qt.WindowType.WindowMinMaxButtonsHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        
        # Center on screen
        self._center_window()
        
        # Setup UI
        self._setup_ui()
        self._setup_tray()
        self._apply_styles()
        
        # Load games
        self._refresh_games()
        
        # Auto-refresh timer for playtime updates
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._refresh_games)
        self.refresh_timer.start(10000)  # Refresh every 10 seconds
    
    def _center_window(self):
        """Center the window on the screen."""
        from PyQt6.QtWidgets import QDesktopWidget
        screen = QApplication.primaryScreen().geometry()
        size = self.geometry()
        self.move(
            (screen.width() - size.width()) // 2,
            (screen.height() - size.height()) // 2
        )
    
    def _setup_ui(self):
        """Set up the main window UI."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Title bar
        title_bar = self._create_title_bar()
        main_layout.addWidget(title_bar)
        
        # Content area
        content_frame = QFrame()
        content_frame.setObjectName("contentFrame")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(15)
        
        # Header with add button
        header_layout = QHBoxLayout()
        
        title = QLabel("🎮 VELOX LAUNCHER")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.ACCENT_COLOR};")
        
        self.add_btn = QPushButton("+ ADD GAME")
        self.add_btn.setFixedHeight(35)
        self.add_btn.clicked.connect(self._add_game)
        
        self.settings_btn = QPushButton("⚙ SETTINGS")
        self.settings_btn.setFixedHeight(35)
        self.settings_btn.clicked.connect(self._show_settings)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.add_btn)
        header_layout.addWidget(self.settings_btn)
        content_layout.addLayout(header_layout)
        
        # Games scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setObjectName("gamesScroll")
        
        self.games_container = QWidget()
        self.games_layout = QVBoxLayout(self.games_container)
        self.games_layout.setSpacing(15)
        self.games_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll_area.setWidget(self.games_container)
        content_layout.addWidget(self.scroll_area)
        
        main_layout.addWidget(content_frame)
    
    def _create_title_bar(self) -> QWidget:
        """Create custom title bar with drag functionality."""
        title_bar = QFrame()
        title_bar.setObjectName("titleBar")
        title_bar.setFixedHeight(40)
        
        layout = QHBoxLayout(title_bar)
        layout.setContentsMargins(15, 0, 10, 0)
        
        # Title/Logo
        logo = QLabel("⚡ VELOX")
        logo.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        logo.setStyleSheet(f"color: {self.ACCENT_COLOR};")
        
        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        # Window controls
        minimize_btn = QPushButton("─")
        minimize_btn.setFixedSize(30, 30)
        minimize_btn.clicked.connect(self.showMinimized)
        
        maximize_btn = QPushButton("□")
        maximize_btn.setFixedSize(30, 30)
        maximize_btn.clicked.connect(self._toggle_maximize)
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.clicked.connect(self._close_app)
        
        layout.addWidget(logo)
        layout.addWidget(spacer)
        layout.addWidget(minimize_btn)
        layout.addWidget(maximize_btn)
        layout.addWidget(close_btn)
        
        return title_bar
    
    def _toggle_maximize(self):
        """Toggle between maximized and normal state."""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
    
    def _close_app(self):
        """Close the application."""
        self.close()
    
    def _setup_tray(self):
        """Set up system tray icon and menu."""
        # Create tray icon
        self.tray_icon = QSystemTrayIcon(self)
        
        # Create simple icon programmatically
        from PyQt6.QtGui import QPixmap, QPainter
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setBrush(QColor(self.ACCENT_COLOR))
        painter.drawEllipse(2, 2, 28, 28)
        painter.setPen(QColor("#000000"))
        painter.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "V")
        painter.end()
        
        icon = QIcon(pixmap)
        self.tray_icon.setIcon(icon)
        
        # Create tray menu
        tray_menu = QMenu()
        
        show_action = tray_menu.addAction("Open Launcher")
        show_action.triggered.connect(self.show)
        
        tray_menu.addSeparator()
        
        exit_action = tray_menu.addAction("Exit")
        exit_action.triggered.connect(self._close_app)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()
    
    def _on_tray_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            self.activateWindow()
    
    def _apply_styles(self):
        """Apply gaming-themed styles to the window."""
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {self.BG_COLOR};
            }}
            
            #titleBar {{
                background-color: #1A1A1A;
                border-bottom: 2px solid {self.ACCENT_COLOR};
            }}
            
            #contentFrame {{
                background-color: {self.CARD_AREA_BG};
            }}
            
            QLabel {{
                color: {self.TEXT_COLOR};
            }}
            
            QPushButton {{
                background-color: transparent;
                border: 2px solid {self.ACCENT_COLOR};
                border-radius: 5px;
                color: {self.ACCENT_COLOR};
                font-weight: bold;
                font-size: 11px;
                padding: 5px 15px;
            }}
            
            QPushButton:hover {{
                background-color: {self.ACCENT_COLOR};
                color: #000000;
            }}
            
            QPushButton:pressed {{
                background-color: #0099CC;
                border-color: #0099CC;
            }}
            
            #titleBar QPushButton {{
                border: none;
                color: #888888;
                font-size: 14px;
                padding: 0;
            }}
            
            #titleBar QPushButton:hover {{
                color: {self.ACCENT_COLOR};
                background-color: transparent;
            }}
            
            #titleBar QPushButton#closeBtn {{
                
            }}
            
            #titleBar QPushButton#closeBtn:hover {{
                background-color: #CC0000;
                color: #FFFFFF;
            }}
            
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            
            QScrollBar:vertical {{
                background-color: #1A1A1A;
                width: 10px;
                border-radius: 5px;
            }}
            
            QScrollBar::handle:vertical {{
                background-color: #333333;
                border-radius: 5px;
                min-height: 20px;
            }}
            
            QScrollBar::handle:vertical:hover {{
                background-color: {self.ACCENT_COLOR};
            }}
            
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
    
    def _refresh_games(self):
        """Refresh the games list from database."""
        # Clear existing cards
        while self.games_layout.count():
            item = self.games_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Get all games
        games = self.db.get_all_games()
        
        if not games:
            # Show empty state
            empty_label = QLabel("No games added yet.\nClick '+ ADD GAME' to get started!")
            empty_label.setFont(QFont("Segoe UI", 14))
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet("color: #666666; padding: 50px;")
            self.games_layout.addWidget(empty_label)
        else:
            # Create game cards
            for game_data in games:
                card = GameCard(game_data)
                card.launch_requested.connect(self._launch_game)
                card.info_requested.connect(self._show_stats)
                self.games_layout.addWidget(card)
            
            self.games_layout.addStretch()
    
    def _add_game(self):
        """Show dialog to add a new game."""
        dialog = AddGameDialog(self)
        
        if dialog.exec() == AddGameDialog.DialogCode.Accepted:
            data = dialog.get_game_data()
            
            # Add to database
            game_id = self.db.add_game(
                name=data['name'],
                exe_path=data['exe_path'],
                cover_image_path=data['cover_image_path']
            )
            
            # Refresh games list
            self._refresh_games()
    
    def _launch_game(self, game_id: int):
        """Launch a game and start tracking."""
        game_data = self.db.get_game(game_id)
        
        if not game_data:
            return
        
        exe_path = game_data['exe_path']
        
        if not os.path.exists(exe_path):
            print(f"Executable not found: {exe_path}")
            return
        
        # Start a new session
        session_id = self.db.start_session(game_id)
        self.active_sessions[game_id] = session_id
        
        # Launch the game
        pid = self.tracker.launch_and_track(exe_path, game_id)
        
        if pid:
            print(f"Launched {game_data['name']} (PID: {pid})")
        else:
            # Failed to launch, end the session
            self.db.end_session(session_id)
            del self.active_sessions[game_id]
    
    def _on_session_end(self, game_id: int, pid: int):
        """Called when a tracked game process ends."""
        # End the session in database
        if game_id in self.active_sessions:
            session_id = self.active_sessions.pop(game_id)
            self.db.end_session(session_id)
            
            # Update UI if window is open
            from PyQt6.QtCore import QMetaObject, Qt
            QMetaObject.invokeMethod(
                self, '_refresh_games',
                Qt.ConnectionType.QueuedConnection
            )
    
    def _show_stats(self, game_id: int):
        """Show statistics window for a game."""
        game_data = self.db.get_game(game_id)
        
        if game_data:
            stats_window = StatsWindow(game_data, self.db, self)
            stats_window.show()
    
    def _show_settings(self):
        """Show settings dialog (placeholder)."""
        # Placeholder for settings - could be expanded
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "Settings",
            "Settings panel placeholder.\n\nFeatures:\n"
            "- Change accent color\n"
            "- Minimize to tray toggle\n"
            "- Font preferences"
        )
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Check if we should minimize to tray instead of closing
        # For now, just close normally
        
        # Stop tracker
        self.tracker.stop_tracking()
        
        # Close database
        self.db.close()
        
        event.accept()


def main():
    """Main entry point for the application."""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setApplicationName("Velox Gaming Launcher")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
