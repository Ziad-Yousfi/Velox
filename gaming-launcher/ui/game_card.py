"""
Game Card Widget for Velox Gaming Launcher.

A card widget displaying game information with:
- Game name
- Total playtime
- Last played date
- Launch button
- Info button (opens stats)
- Hover glow effects
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QPixmap, QPainter, QColor


class GameCard(QFrame):
    """Individual game card widget with gaming aesthetic."""
    
    # Signals
    launch_requested = pyqtSignal(int)  # game_id
    info_requested = pyqtSignal(int)    # game_id
    
    # Styling constants
    BG_COLOR = "#1A1A1A"
    HOVER_BG = "#252525"
    ACCENT_COLOR = "#00D4FF"
    TEXT_COLOR = "#FFFFFF"
    SECONDARY_TEXT = "#888888"
    
    def __init__(self, game_data: dict, parent=None):
        super().__init__(parent)
        self.game_id = game_data['id']
        self.game_name = game_data['name']
        self.total_playtime = game_data.get('total_playtime_seconds', 0)
        self.last_played = game_data.get('last_played')
        self.cover_path = game_data.get('cover_image_path')
        
        self.setMinimumSize(280, 180)
        self.setMaximumSize(350, 220)
        self.setFixedSize(280, 180)
        
        # Track hover state
        self._hovered = False
        
        self._setup_ui()
        self._apply_styles()
        self._setup_effects()
    
    def _setup_ui(self):
        """Set up the card UI components."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create card container
        self.card_container = QFrame()
        self.card_container.setObjectName("cardContainer")
        card_layout = QVBoxLayout(self.card_container)
        card_layout.setContentsMargins(15, 15, 15, 15)
        card_layout.setSpacing(10)
        
        # Cover image area (placeholder if no cover)
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(250, 100)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setStyleSheet("""
            background-color: #0D0D0D;
            border-radius: 5px;
        """)
        
        if self.cover_path:
            self._load_cover_image()
        else:
            # Show game initials as placeholder
            initials = self._get_initials()
            self.cover_label.setText(initials)
            self.cover_label.setStyleSheet(f"""
                background-color: #0D0D0D;
                border-radius: 5px;
                color: {self.ACCENT_COLOR};
                font-size: 32px;
                font-weight: bold;
            """)
        
        card_layout.addWidget(self.cover_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        
        # Game name
        self.name_label = QLabel(self.game_name)
        self.name_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setWordWrap(True)
        self.name_label.setMaximumWidth(220)
        card_layout.addWidget(self.name_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        
        # Playtime and last played
        info_layout = QHBoxLayout()
        info_layout.setSpacing(15)
        
        self.playtime_label = QLabel(self._format_playtime())
        self.playtime_label.setFont(QFont("Segoe UI", 9))
        self.playtime_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.last_played_label = QLabel(self._format_last_played())
        self.last_played_label.setFont(QFont("Segoe UI", 9))
        self.last_played_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        info_layout.addWidget(self.playtime_label)
        info_layout.addWidget(self.last_played_label)
        card_layout.addLayout(info_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        self.launch_btn = QPushButton("▶ LAUNCH")
        self.launch_btn.setFixedHeight(32)
        self.launch_btn.clicked.connect(self._on_launch_clicked)
        
        self.info_btn = QPushButton("📊 STATS")
        self.info_btn.setFixedHeight(32)
        self.info_btn.clicked.connect(self._on_info_clicked)
        
        button_layout.addWidget(self.launch_btn)
        button_layout.addWidget(self.info_btn)
        card_layout.addLayout(button_layout)
        
        main_layout.addWidget(self.card_container)
    
    def _apply_styles(self):
        """Apply gaming-themed styles."""
        self.setStyleSheet(f"""
            GameCard {{
                background-color: transparent;
                border: none;
            }}
            
            #cardContainer {{
                background-color: {self.BG_COLOR};
                border: 2px solid #333333;
                border-radius: 10px;
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
                font-size: 10px;
                padding: 5px 10px;
            }}
            
            QPushButton:hover {{
                background-color: {self.ACCENT_COLOR};
                color: #000000;
            }}
            
            QPushButton:pressed {{
                background-color: #0099CC;
                border-color: #0099CC;
            }}
        """)
    
    def _setup_effects(self):
        """Set up visual effects like shadows and glow."""
        # Drop shadow for depth
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 100))
        self.card_container.setGraphicsEffect(shadow)
        self._shadow = shadow
    
    def _get_initials(self) -> str:
        """Get initials from game name for placeholder."""
        words = self.game_name.split()
        if len(words) >= 2:
            return (words[0][0] + words[1][0]).upper()
        elif len(words) == 1 and len(words[0]) >= 2:
            return words[0][:2].upper()
        return "??"
    
    def _load_cover_image(self):
        """Load and display cover image."""
        try:
            pixmap = QPixmap(self.cover_path)
            if not pixmap.isNull():
                # Scale to fit
                scaled = pixmap.scaled(
                    250, 100,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.cover_label.setPixmap(scaled)
                self.cover_label.setText("")
        except Exception as e:
            print(f"Failed to load cover image: {e}")
    
    def _format_playtime(self) -> str:
        """Format total playtime as human-readable string."""
        hours = self.total_playtime // 3600
        minutes = (self.total_playtime % 3600) // 60
        if hours > 0:
            return f"⏱ {hours}h {minutes}m"
        else:
            return f"⏱ {minutes}m"
    
    def _format_last_played(self) -> str:
        """Format last played date."""
        if not self.last_played:
            return "Never played"
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(self.last_played)
            return dt.strftime("%b %d")
        except (ValueError, TypeError):
            return str(self.last_played)[:10]
    
    def update_playtime(self, total_seconds: int):
        """Update the displayed playtime."""
        self.total_playtime = total_seconds
        self.playtime_label.setText(self._format_playtime())
    
    def enterEvent(self, event):
        """Handle mouse enter - add glow effect."""
        self._hovered = True
        self.card_container.setStyleSheet(f"""
            #cardContainer {{
                background-color: {self.HOVER_BG};
                border: 2px solid {self.ACCENT_COLOR};
                border-radius: 10px;
            }}
        """)
        
        # Enhance shadow for glow effect
        self._shadow.setColor(QColor(0, 212, 255, 80))  # Neon blue glow
        self._shadow.setBlurRadius(25)
        
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave - remove glow effect."""
        self._hovered = False
        self.card_container.setStyleSheet(f"""
            #cardContainer {{
                background-color: {self.BG_COLOR};
                border: 2px solid #333333;
                border-radius: 10px;
            }}
        """)
        
        # Reset shadow
        self._shadow.setColor(QColor(0, 0, 0, 100))
        self._shadow.setBlurRadius(15)
        
        super().leaveEvent(event)
    
    def _on_launch_clicked(self):
        """Emit launch signal."""
        self.launch_requested.emit(self.game_id)
    
    def _on_info_clicked(self):
        """Emit info/stats signal."""
        self.info_requested.emit(self.game_id)
