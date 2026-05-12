"""
Add Game Dialog for Velox Gaming Launcher.

A dialog that allows users to add a new game/application by:
- Selecting an executable file
- Setting a custom name
- Optionally selecting a cover image
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont


class AddGameDialog(QDialog):
    """Dialog for adding a new game to the launcher."""
    
    # Neon accent color
    ACCENT_COLOR = "#00D4FF"
    BG_COLOR = "#1A1A1A"
    INPUT_BG = "#252525"
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Game")
        self.setMinimumSize(450, 280)
        self.setMaximumSize(450, 350)
        self.setModal(True)
        
        # Remove window frame for custom look
        self.setWindowFlags(
            Qt.WindowType.Dialog | 
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowSystemMenuHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        
        # Store selected paths
        self.exe_path = ""
        self.cover_path = None
        
        self._setup_ui()
        self._apply_styles()
    
    def _setup_ui(self):
        """Set up the dialog UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("ADD NEW GAME")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Game name input
        name_layout = QVBoxLayout()
        name_label = QLabel("Game Name:")
        name_label.setFont(QFont("Segoe UI", 10))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter game name...")
        self.name_input.setFont(QFont("Segoe UI", 11))
        self.name_input.setFixedHeight(35)
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)
        
        # Executable path
        exe_layout = QVBoxLayout()
        exe_label = QLabel("Executable (.exe):")
        exe_label.setFont(QFont("Segoe UI", 10))
        
        exe_input_layout = QHBoxLayout()
        self.exe_input = QLineEdit()
        self.exe_input.setPlaceholderText("Select game executable...")
        self.exe_input.setFont(QFont("Segoe UI", 10))
        self.exe_input.setReadOnly(True)
        self.exe_input.setFixedHeight(35)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.setFixedHeight(35)
        browse_btn.clicked.connect(self._browse_exe)
        
        exe_input_layout.addWidget(self.exe_input)
        exe_input_layout.addWidget(browse_btn)
        exe_layout.addWidget(exe_label)
        exe_layout.addLayout(exe_input_layout)
        layout.addLayout(exe_layout)
        
        # Cover image path (optional)
        cover_layout = QVBoxLayout()
        cover_label = QLabel("Cover Image (Optional):")
        cover_label.setFont(QFont("Segoe UI", 10))
        
        cover_input_layout = QHBoxLayout()
        self.cover_input = QLineEdit()
        self.cover_input.setPlaceholderText("Select cover image...")
        self.cover_input.setFont(QFont("Segoe UI", 10))
        self.cover_input.setReadOnly(True)
        self.cover_input.setFixedHeight(35)
        
        cover_browse_btn = QPushButton("Browse...")
        cover_browse_btn.setFixedHeight(35)
        cover_browse_btn.clicked.connect(self._browse_cover)
        
        cover_input_layout.addWidget(self.cover_input)
        cover_input_layout.addWidget(cover_browse_btn)
        cover_layout.addWidget(cover_label)
        cover_layout.addLayout(cover_input_layout)
        layout.addLayout(cover_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        cancel_btn = QPushButton("CANCEL")
        cancel_btn.setFixedHeight(40)
        cancel_btn.clicked.connect(self.reject)
        
        add_btn = QPushButton("ADD GAME")
        add_btn.setFixedHeight(40)
        add_btn.clicked.connect(self._on_add_clicked)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(add_btn)
        layout.addLayout(button_layout)
    
    def _apply_styles(self):
        """Apply gaming-themed styles to the dialog."""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.BG_COLOR};
                border: 2px solid {self.ACCENT_COLOR};
                border-radius: 10px;
            }}
            
            QLabel {{
                color: #FFFFFF;
            }}
            
            QLineEdit {{
                background-color: {self.INPUT_BG};
                border: 1px solid #333333;
                border-radius: 5px;
                padding: 5px 10px;
                color: #FFFFFF;
                selection-background-color: {self.ACCENT_COLOR};
            }}
            
            QLineEdit:focus {{
                border: 1px solid {self.ACCENT_COLOR};
            }}
            
            QPushButton {{
                background-color: transparent;
                border: 2px solid {self.ACCENT_COLOR};
                border-radius: 5px;
                color: {self.ACCENT_COLOR};
                font-weight: bold;
                font-size: 11px;
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
    
    def _browse_exe(self):
        """Open file dialog to select executable."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Game Executable",
            "",
            "Executable Files (*.exe);;All Files (*)"
        )
        
        if file_path:
            self.exe_path = file_path
            self.exe_input.setText(file_path)
            
            # Auto-fill name from executable if name is empty
            if not self.name_input.text().strip():
                name = self._extract_name_from_exe(file_path)
                self.name_input.setText(name)
    
    def _browse_cover(self):
        """Open file dialog to select cover image."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Cover Image",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp);;All Files (*)"
        )
        
        if file_path:
            self.cover_path = file_path
            self.cover_input.setText(file_path)
    
    def _extract_name_from_exe(self, exe_path: str) -> str:
        """Extract a game name from the executable path."""
        import os
        # Get filename without extension
        name = os.path.basename(exe_path)
        name = os.path.splitext(name)[0]
        
        # Clean up common suffixes
        for suffix in ['_win64', '_win32', '-win64', '-win32', 
                       '_release', '-release', '_game', '-game']:
            if name.lower().endswith(suffix):
                name = name[:-len(suffix)]
        
        # Replace underscores and hyphens with spaces
        name = name.replace('_', ' ').replace('-', ' ')
        
        # Title case
        name = name.title()
        
        return name
    
    def _on_add_clicked(self):
        """Validate and accept the dialog."""
        name = self.name_input.text().strip()
        
        if not name:
            self.name_input.setFocus()
            self.name_input.setStyleSheet("""
                QLineEdit {
                    background-color: #3a1a1a;
                    border: 1px solid #ff4444;
                }
            """)
            return
        
        if not self.exe_path:
            self.exe_input.setStyleSheet("""
                QLineEdit {
                    background-color: #3a1a1a;
                    border: 1px solid #ff4444;
                }
            """)
            return
        
        # Reset styles
        self.name_input.setStyleSheet("")
        self.exe_input.setStyleSheet("")
        
        self.accept()
    
    def get_game_data(self) -> dict:
        """Get the entered game data."""
        return {
            'name': self.name_input.text().strip(),
            'exe_path': self.exe_path,
            'cover_image_path': self.cover_path
        }
