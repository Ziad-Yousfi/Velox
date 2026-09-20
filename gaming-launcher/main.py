"""
Velox Gaming Launcher - Main Entry Point

A lightweight, high-performance gaming launcher for Windows with:
- Game library management
- Automatic playtime tracking
- Detailed statistics with charts and calendar heatmap
- Gaming aesthetic with dark theme and neon accents

Tech Stack Justification:
=========================
We chose Python + PyQt6 for this project because:

1. RAM Efficiency: PyQt6 is a native binding to Qt6, which is written in C++.
   When properly optimized, it consumes significantly less RAM than Electron
   (which bundles Chromium) while still providing a modern UI.

2. Cross-platform Compatibility: While targeting Windows, PyQt6 ensures the
   code could be adapted for Linux/macOS if needed.

3. Native Look and Feel: Qt provides native widgets that integrate well with
   the OS while allowing complete customization for our gaming theme.

4. Rapid Development: Python allows for quick iteration and clean code structure
   without sacrificing performance for this use case.

5. SQLite Integration: Python's built-in sqlite3 module is highly efficient
   and doesn't require additional dependencies.

RAM Optimization Strategies Implemented:
========================================
1. Lazy loading of game cover images - only visible items are loaded
2. Polling every 5 seconds instead of continuous monitoring
3. Single SQLite connection with WAL mode and query caching
4. Vector-based UI elements (no large image assets)
5. Background thread for process tracking that never blocks UI
6. System tray support with minimal footprint when minimized
7. No heavy frameworks like Electron or CEF

Expected Memory Usage:
- Main launcher (idle): ~40-60 MB
- With games loaded: ~50-70 MB  
- Tray-only tracker: ~10-15 MB
"""

import sys
import os
from pathlib import Path

# Add the gaming-launcher directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Windows Taskbar Icon Integration ──────────────────────────────────────────
if sys.platform == "win32":
    import ctypes
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("velox.gaming.launcher.1.0")
    except Exception:
        pass

# ── Load custom fonts before creating QApplication ────────────────────────────
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFontDatabase, QFont, QIcon
from PyQt6.QtCore import Qt

QApplication.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
)
_app = QApplication.instance() or QApplication(sys.argv)
_app.setApplicationName("Velox Gaming Launcher")

def get_resource_path(rel_path: str) -> Path:
    """Get absolute path to resource, works for dev and for PyInstaller."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / rel_path
    return Path(__file__).parent / rel_path

# Set application icon
_ico_path = get_resource_path("icon/velox.ico")
if _ico_path.exists():
    _app.setWindowIcon(QIcon(str(_ico_path)))

# Register Rajdhani font family
_fonts_dir = get_resource_path("assets/fonts")
if _fonts_dir.exists():
    for _ttf in _fonts_dir.glob("Rajdhani*.ttf"):
        QFontDatabase.addApplicationFont(str(_ttf))

# Set Rajdhani as the application-wide default font
_app.setFont(QFont("Rajdhani", 10))

from ui.main_window import main


if __name__ == "__main__":
    main(_app)

